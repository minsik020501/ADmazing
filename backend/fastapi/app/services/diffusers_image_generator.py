"""Hugging Face diffusers 모델로 이미지를 생성하는 생성기.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from app.core.config import settings
from app.services.gpu_out_of_memory_error import GpuOutOfMemoryError
from app.utils.image import to_base64


class DiffusersImageGenerator:
    """MODEL_PATH(Hugging Face 이름 또는 /models 산출물)에서 모델을 불러와 생성한다."""

    def __init__(self) -> None:
        """사용 가능한 디바이스를 선택하고 파이프라인과 LoRA 가중치를 로드한다."""
        import torch
        from diffusers import AutoPipelineForText2Image

        self._torch = torch
        if torch.cuda.is_available():
            self.device, dtype = "cuda", torch.float16
        elif torch.backends.mps.is_available():
            self.device, dtype = "mps", torch.float32
        else:
            self.device, dtype = "cpu", torch.float32

        self.pipe = AutoPipelineForText2Image.from_pretrained(
            settings.model_path,
            torch_dtype=dtype,
            token=settings.hf_token or None,
        )
        if settings.lora_path:
            self.pipe.load_lora_weights(settings.lora_path)
        self.pipe.to(self.device)

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seeds: list[int],
    ) -> list[str]:
        """로드된 모델로 seed 개수만큼 이미지를 한 번에(배치로) 생성한다.

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
        # 이미지마다 생성기를 따로 두어야 seed 하나로 해당 이미지를 재현할 수 있다
        generators = [
            self._torch.Generator(device=self.device).manual_seed(seed)
            for seed in seeds
        ]

        try:
            images = self.pipe(
                prompt=prompt,
                num_inference_steps=settings.num_inference_steps,
                guidance_scale=settings.guidance_scale,
                width=width,
                height=height,
                num_images_per_prompt=len(seeds),
                generator=generators,
            ).images
        except self._torch.cuda.OutOfMemoryError as e:
            self._torch.cuda.empty_cache()
            raise GpuOutOfMemoryError from e
        return [to_base64(image) for image in images]
