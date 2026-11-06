"""추천 문구 하나의 스키마.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field


class CopySuggestion(BaseModel):
    """추천 목록의 문구 하나."""

    text: str = Field(
        ..., description="문구. 필수 단어가 있으면 모두 글자 그대로 들어 있다"
    )
