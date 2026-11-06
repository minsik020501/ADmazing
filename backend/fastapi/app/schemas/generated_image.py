"""생성된 이미지 한 장의 스키마.

생성일자: 2026-10-22
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field

from app.schemas.image_copies import ImageCopies


class GeneratedImage(BaseModel):
    """생성된 이미지, 재현에 사용할 seed, 이 이미지에 맞춘 추천 문구."""

    image_base64: str = Field(..., description="PNG 이미지의 base64 문자열")
    seed: int = Field(..., description="이 이미지를 생성한 seed")
    copies: ImageCopies | None = Field(
        None, description="이 이미지에 맞춘 역할별 추천 문구. 추천에 실패하면 null"
    )
    copies_error: str | None = Field(
        None, description="문구 추천에 실패했을 때 화면에 보여줄 메시지"
    )
