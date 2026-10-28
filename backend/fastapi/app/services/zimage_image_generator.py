"""Z-Image-Turbo 모델로 이미지를 생성하는 생성기.

backend/ai/compare_ratios.py의 Z-Image 로딩 방식을 서버용으로 옮긴 것이다.

생성일자: 2026-10-28
생성자: ven_choi
수정일자: 2026-10-28
수정자: ven_choi
"""

import threading

from app.core.config import settings
from app.services.gpu_out_of_memory_error import GpuOutOfMemoryError
from app.utils.device import resolve_device
from app.utils.image import to_base64


class ZImageImageGenerator:
    """ZIMAGE_MODEL_DIR에서 Z-Image-Turbo 모델을 불러와 생성한다."""

    def __init__(self) -> None:
        """디바이스를 선택하고 Z-Image 파이프라인을 디바이스에 맞게 로드한다.

        Raises:
            FileNotFoundError: 모델 폴더가 없을 때.
            RuntimeError: 요청한 디바이스를 사용할 수 없을 때.
        """
        import torch
        from diffusers import ZImagePipeline

        self._torch = torch
        self.device = resolve_device(settings.zimage_device)
        # 파이프라인 하나를 여러 요청이 동시에 돌리지 않도록 한 번에 하나씩 처리한다
        self._lock = threading.Lock()

        model_dir = settings.zimage_model_dir
        if not model_dir.exists():
            raise FileNotFoundError(
                f"Z-Image 모델 폴더가 없습니다: {model_dir}. "
                "레포 루트의 models/에 모델을 받았는지 확인하세요."
            )

        # bf16으로 올려 fp32 대비 메모리를 절반으로 줄인다 (모델 카드 권장).
        # CPU는 bf16 연산이 느려서 float32로 올린다
        dtype = torch.float32 if self.device == "cpu" else torch.bfloat16

        use_offload = self.device == "cuda" and settings.zimage_use_offload
        # cuda에서 오프로드가 아니면 GPU로 바로 불러온다. 모델 전체(bf16 약 19GB)를
        # CPU 램에 먼저 올리지 않으므로 램이 모델보다 작은 서버에서도 로드된다.
        # mps는 램과 메모리를 함께 써서 이득이 없고, 바로 불러오면 로딩이 멈춘다
        device_map = "cuda" if self.device == "cuda" and not use_offload else None

        self.pipe = ZImagePipeline.from_pretrained(
            model_dir, torch_dtype=dtype, device_map=device_map
        )

        if use_offload:
            # 계산은 GPU, 쓰지 않는 부품은 CPU 램에 보관 (램이 모델 전체보다 커야 한다)
            self.pipe.enable_model_cpu_offload()
        elif device_map is None:
            self.pipe.to(self.device)

        # VRAM 피크는 VAE 디코딩에서 생긴다 (L4 24GB에서 여유 1GB 미만).
        # 배치를 한 장씩, 한 장은 타일로 나눠 디코딩해 피크를 낮춘다
        self.pipe.vae.enable_slicing()
        self.pipe.vae.enable_tiling()
        # 이 VAE는 기본 타일이 1024px라 1024×1024 이하는 나누지 않아 효과가 없다.
        # 512px(latent 64) 타일로 줄여 모든 비율에서 타일 디코딩이 동작하게 한다
        self.pipe.vae.tile_sample_min_size = 512
        self.pipe.vae.tile_latent_min_size = 64

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seeds: list[int],
    ) -> list[str]:
        """로드된 Z-Image 파이프라인으로 seed 개수만큼 이미지를 한 번에(배치로) 생성한다.

        Args:
            prompt: 영어 프롬프트.
            width: 이미지 너비 (16의 배수).
            height: 이미지 높이 (16의 배수).
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
                    num_inference_steps=settings.zimage_steps,
                    # Turbo 모델은 CFG 없이 학습되어 0으로 고정한다
                    guidance_scale=0.0,
                    width=width,
                    height=height,
                    num_images_per_prompt=len(seeds),
                    generator=generators,
                ).images
            except self._torch.cuda.OutOfMemoryError as e:
                self._torch.cuda.empty_cache()
                raise GpuOutOfMemoryError from e
        return [to_base64(image) for image in images]
