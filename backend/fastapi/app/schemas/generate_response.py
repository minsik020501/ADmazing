"""이미지 생성 응답 스키마.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from pydantic import BaseModel, Field

from app.core.image_ratio import ImageRatio
from app.schemas.generated_image import GeneratedImage


class GenerateResponse(BaseModel):
    """이미지 생성 API 응답 본문."""

    original_prompt: str
    translated_prompt: str
    ratio: ImageRatio = Field(..., description="요청한 이미지 비율")
    width: int = Field(..., description="생성된 이미지 너비 (px)")
    height: int = Field(..., description="생성된 이미지 높이 (px)")
    images: list[GeneratedImage] = Field(
        ..., description="생성된 이미지 목록 (NUM_IMAGES_PER_REQUEST 장)"
    )
