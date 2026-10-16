"""이미지 생성 요청 스키마.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """이미지 생성 API 요청 본문."""

    prompt: str = Field(..., min_length=1, description="한국어 광고 이미지 설명")
    seed: int | None = None
    width: int | None = Field(
        None,
        ge=256,
        le=1536,
        multiple_of=8,
        description="이미지 너비 (8의 배수). 없으면 DEFAULT_IMAGE_WIDTH 사용",
    )
    height: int | None = Field(
        None,
        ge=256,
        le=1536,
        multiple_of=8,
        description="이미지 높이 (8의 배수). 없으면 DEFAULT_IMAGE_HEIGHT 사용",
    )
