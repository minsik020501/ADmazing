"""이미지 한 장에 대한 역할별 추천 문구 스키마.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field

from app.core.copy_role import COPIES_PER_ROLE
from app.core.layout_templates import MAX_STYLES, FontStyle
from app.schemas.copy_suggestion import CopySuggestion

_ROLE_DESCRIPTION = (
    f"1~{COPIES_PER_ROLE}개. title[i], subtitle[i], text[i]가 한 묶음(칩 하나)으로 "
    "어울리게 쓰였고, 세 목록의 길이는 같다"
)


class ImageCopies(BaseModel):
    """이미지 한 장에 어울리는 title, subtitle, text 문구 목록과 강조색·글꼴 스타일·대표색.

    같은 번호의 문구끼리 한 광고로 읽히도록 묶어서 추천한다.
    """

    title: list[CopySuggestion] = Field(..., description=f"타이틀. {_ROLE_DESCRIPTION}")
    subtitle: list[CopySuggestion] = Field(
        ..., description=f"서브타이틀. {_ROLE_DESCRIPTION}"
    )
    text: list[CopySuggestion] = Field(..., description=f"본문. {_ROLE_DESCRIPTION}")
    accent: str | None = Field(
        None,
        description="이미지를 보고 고른 문구 강조색 #RRGGBB. 문구 배치 추천 요청의 accent로 "
        "그대로 보내면 된다. 고르지 못하면 null",
    )
    styles: list[FontStyle] = Field(
        default_factory=list,
        description=f"이미지에 어울리는 글꼴 스타일 (어울리는 순서, 최대 {MAX_STYLES}개). "
        "문구 배치 추천 요청의 styles로 그대로 보내면 된다. 고르지 못하면 빈 목록",
    )
    palette: list[str] = Field(
        default_factory=list,
        description="이미지의 대표색 #RRGGBB (많이 쓰인 순서, 최대 5개). "
        "글자색을 고를 때 기본색으로 쓴다",
    )
