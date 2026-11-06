"""추천 문구 하나의 스키마.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Literal

from pydantic import BaseModel, Field


class CopySuggestion(BaseModel):
    """추천 목록의 문구 하나와 출처."""

    text: str = Field(..., description="문구")
    source: Literal["user", "ai"] = Field(
        ..., description="user: 사용자가 직접 넣은 문장, ai: AI가 추천한 문구"
    )
