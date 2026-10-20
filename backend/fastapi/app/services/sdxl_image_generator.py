"""SDXL 기본 모델 + fp16 VAE로 이미지를 생성하는 생성기.

backend/ai/sdxl_pipeline.py의 로딩 방식을 서버용으로 옮긴 것이다.
api 컨테이너에는 backend/ai가 없으므로 직접 import하지 않는다.

생성일자: 2026-10-20
생성자: ven_choi
수정일자: 2026-10-20
수정자: ven_choi
"""

import threading

from app.core.config import settings
from app.utils.image import to_base64


class SdxlImageGenerator:
    """SDXL_MODEL_DIR, SDXL_VAE_DIR에서 모델을 불러와 생성한다."""

    def __init__(self) -> None:
        """디바이스를 선택하고 SDXL 파이프라인을 디바이스에 맞게 로드한다.

        Raises:
            FileNotFoundError: 모델 폴더가 없을 때.
            RuntimeError: 요청한 디바이스를 사용할 수 없을 때.
        """
        import torch
        from diffusers import AutoencoderKL, StableDiffusionXLPipeline

        self._torch = torch
        self.device = self._resolve_device(settings.sdxl_device)
        # 파이프라인 하나를 여러 요청이 동시에 돌리지 않도록 한 번에 하나씩 처리한다
        self._lock = threading.Lock()

        model_dir, vae_dir = settings.sdxl_model_dir, settings.sdxl_vae_dir
        if not model_dir.exists() or not vae_dir.exists():
            raise FileNotFoundError(
                f"SDXL 모델 폴더가 없습니다: {model_dir}, {vae_dir}. "
                "레포 루트의 models/에 모델을 받았는지 확인하세요."
            )

        # CPU는 fp16 연산을 제대로 지원하지 않아서 float32로 올린다
        dtype = torch.float32 if self.device == "cpu" else torch.float16

        vae = AutoencoderKL.from_pretrained(vae_dir, torch_dtype=dtype)
        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            model_dir,
            vae=vae,
            torch_dtype=dtype,
            variant="fp16",
            use_safetensors=True,
        )

        if self.device == "cuda" and settings.sdxl_use_offload:
            # 계산은 GPU, 쓰지 않는 부품은 CPU 램에 보관 (.to("cuda")와 함께 쓰지 않는다)
            self.pipe.enable_model_cpu_offload()
        else:
            self.pipe.to(self.device)
            if self.device == "mps":
                # 통합 메모리 64GB 미만 Mac에서 메모리 피크를 낮춘다
                self.pipe.enable_attention_slicing()

        self.pipe.vae.enable_tiling()

    def _resolve_device(self, name: str) -> str:
        """요청한 디바이스가 사용 가능한지 확인하고 실제 사용할 디바이스를 결정한다.

        Args:
            name: auto, cuda, mps, cpu 중 하나. auto면 cuda → mps → cpu 순으로 선택한다.

        Returns:
            str: 실제 사용할 디바이스 이름 (cuda, mps, cpu).

        Raises:
            RuntimeError: 요청한 디바이스를 현재 환경에서 사용할 수 없을 때.
        """
        available = {
            "cuda": self._torch.cuda.is_available(),
            "mps": self._torch.backends.mps.is_available(),
            "cpu": True,
        }
        if name == "auto":
            return next(device for device, ok in available.items() if ok)
        if not available[name]:
            raise RuntimeError(f"'{name}' 디바이스를 사용할 수 없습니다.")
        return name

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int | None = None,
    ) -> str:
        """로드된 SDXL 파이프라인으로 이미지를 생성한다.

        Args:
            prompt: 영어 프롬프트.
            width: 이미지 너비.
            height: 이미지 높이.
            seed: 재현용 랜덤 시드. None이면 매번 다른 이미지를 생성한다.

        Returns:
            str: PNG 이미지의 base64 문자열.
        """
        generator = None
        if seed is not None:
            # 디바이스와 상관없이 같은 seed면 같은 그림이 나오도록 CPU 생성기를 쓴다
            generator = self._torch.Generator(device="cpu").manual_seed(seed)

        with self._lock:
            image = self.pipe(
                prompt=prompt,
                negative_prompt=settings.sdxl_negative_prompt,
                num_inference_steps=settings.sdxl_steps,
                guidance_scale=settings.sdxl_guidance_scale,
                width=width,
                height=height,
                generator=generator,
            ).images[0]
        return to_base64(image)
