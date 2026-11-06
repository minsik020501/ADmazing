"""문구 추천기가 한 번에 돌려주는 결과 (정리 전 문구 후보와 강조색).

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import NamedTuple

from app.core.copy_role import CopyRole
from app.core.layout_templates import FontStyle


class CopyCandidates(NamedTuple):
    """역할별 문구 후보와, 이미지를 보고 고른 강조색·글꼴 스타일."""

    # 역할별 문구 후보 (정리·중복 제거 전)
    copies: dict[CopyRole, list[str]]
    # 문구 강조색 #RRGGBB. 고르지 못했거나 형식이 틀리면 None
    accent: str | None
    # 이미지에 어울리는 글꼴 스타일 (어울리는 순서, 최대 MAX_STYLES개). 없으면 빈 목록
    styles: list[FontStyle]
