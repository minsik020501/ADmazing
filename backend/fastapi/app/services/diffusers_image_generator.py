"""Hugging Face diffusers 모델로 이미지를 생성하는 생성기.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

from app.core.config import settings
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
        seed: int | None = None,
    ) -> str:
        """로드된 모델로 이미지를 생성한다.

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
            generator = self._torch.Generator(device=self.device).manual_seed(seed)

        image = self.pipe(
            prompt=prompt,
            num_inference_steps=settings.num_inference_steps,
            guidance_scale=settings.guidance_scale,
            width=width,
            height=height,
            generator=generator,
        ).images[0]
        return to_base64(image)
