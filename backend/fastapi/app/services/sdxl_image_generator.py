"""SDXL 기본 모델 + fp16 VAE로 이미지를 생성하는 생성기.

backend/ai/sdxl_pipeline.py의 로딩 방식을 서버용으로 옮긴 것이다.
api 컨테이너에는 backend/ai가 없으므로 직접 import하지 않는다.

생성일자: 2026-10-20
생성자: ven_choi
수정일자: 2026-10-28
수정자: ven_choi
"""

import threading

from app.core.config import settings
from app.services.gpu_out_of_memory_error import GpuOutOfMemoryError
from app.utils.device import resolve_device
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
        self.device = resolve_device(settings.sdxl_device)
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

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seeds: list[int],
    ) -> list[str]:
        """로드된 SDXL 파이프라인으로 seed 개수만큼 이미지를 한 번에(배치로) 생성한다.

        Args:
            prompt: 영어 프롬프트.
            width: 이미지 너비.
            height: 이미지 높이.
            seeds: 이미지마다 사용할 seed 목록. 목록 길이만큼 이미지를 생성한다.

        Returns:
            list[str]: seeds 순서대로 생성한 PNG 이미지의 base64 문자열 목록.

        Raises:
            GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
        """
        # 디바이스와 상관없이 같은 seed면 같은 그림이 나오도록 CPU 생성기를 쓴다.
        # 이미지마다 생성기를 따로 두어야 seed 하나로 해당 이미지를 재현할 수 있다
        generators = [
            self._torch.Generator(device="cpu").manual_seed(seed) for seed in seeds
        ]

        with self._lock:
            try:
                images = self.pipe(
                    prompt=prompt,
                    negative_prompt=settings.sdxl_negative_prompt,
                    num_inference_steps=settings.sdxl_steps,
                    guidance_scale=settings.sdxl_guidance_scale,
                    width=width,
                    height=height,
                    num_images_per_prompt=len(seeds),
                    generator=generators,
                ).images
            except self._torch.cuda.OutOfMemoryError as e:
                self._torch.cuda.empty_cache()
                raise GpuOutOfMemoryError from e
        return [to_base64(image) for image in images]
