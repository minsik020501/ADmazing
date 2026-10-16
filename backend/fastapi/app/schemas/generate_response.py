"""이미지 생성 응답 스키마.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

from pydantic import BaseModel


class GenerateResponse(BaseModel):
    """이미지 생성 API 응답 본문."""

    original_prompt: str
    translated_prompt: str
    image_base64: str
