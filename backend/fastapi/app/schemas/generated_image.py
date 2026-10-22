"""생성된 이미지 한 장의 스키마.

생성일자: 2026-10-22
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from pydantic import BaseModel, Field


class GeneratedImage(BaseModel):
    """생성된 이미지와 재현에 사용할 seed."""

    image_base64: str = Field(..., description="PNG 이미지의 base64 문자열")
    seed: int = Field(..., description="이 이미지를 생성한 seed")
