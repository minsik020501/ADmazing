"""이미지 한 장에 대한 역할별 추천 문구 스키마.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field

from app.core.copy_role import COPIES_PER_ROLE
from app.schemas.copy_suggestion import CopySuggestion

_ROLE_DESCRIPTION = (
    f"최대 {COPIES_PER_ROLE}개. 사용자 문장(source=user)이 넣은 순서대로 앞에 오고 "
    "나머지를 AI 문구로 채운다"
)


class ImageCopies(BaseModel):
    """이미지 한 장에 어울리는 title, subtitle, text 문구 목록."""

    title: list[CopySuggestion] = Field(..., description=f"타이틀. {_ROLE_DESCRIPTION}")
    subtitle: list[CopySuggestion] = Field(
        ..., description=f"서브타이틀. {_ROLE_DESCRIPTION}"
    )
    text: list[CopySuggestion] = Field(..., description=f"본문. {_ROLE_DESCRIPTION}")
