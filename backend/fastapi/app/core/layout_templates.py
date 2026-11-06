"""광고 문구 배치 템플릿과 글꼴 짝.

모든 템플릿은 같은 원칙을 따른다.
    - 안전 여백: 짧은 변의 7%
    - 글자 크기: 짧은 변 기준 title 8.5%, subtitle 4%, text 3%
    - 굵기 대비: title만 굵게
    - title → subtitle → text를 한 덩어리 블록으로 쌓고 간격을 일정하게 둔다
    - 외곽선·배경 상자는 쓰지 않는다

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Literal, NamedTuple

from app.core.copy_role import CopyRole


class LayoutTemplate(NamedTuple):
    """문구 블록을 둘 자리."""

    name: str
    # 블록의 세로 기준: 위쪽 여백에 붙임, 아래쪽 여백에 붙임, 세로 가운데
    anchor: Literal["top", "bottom", "middle"]
    align: Literal["left", "center", "right"]
    # 블록 폭 (짧은 변 대비)
    width: float


TEMPLATES: dict[str, LayoutTemplate] = {
    "top_left": LayoutTemplate("좌상단 블록", "top", "left", 0.62),
    "bottom_left": LayoutTemplate("좌하단 블록", "bottom", "left", 0.62),
    "top_right": LayoutTemplate("우상단 블록", "top", "right", 0.62),
    "bottom_right": LayoutTemplate("우하단 블록", "bottom", "right", 0.62),
    "top_center": LayoutTemplate("상단 중앙", "top", "center", 0.8),
    "bottom_center": LayoutTemplate("하단 중앙", "bottom", "center", 0.8),
    "side_left": LayoutTemplate("왼쪽 칼럼", "middle", "left", 0.42),
    "side_right": LayoutTemplate("오른쪽 칼럼", "middle", "right", 0.42),
}

# 글꼴 스타일 id. 문구 추천(OpenAI)이 이미지에 맞는 스타일을 이 중에서 고른다
FontStyle = Literal[
    "minimal_gothic",
    "serif",
    "clean",
    "handwriting",
    "signature",
    "impact_sale",
    "rounded",
]

# 문구 추천이 고르는 스타일 수 (어울리는 순서)
MAX_STYLES = 3

# 스타일별 (제목 글꼴, 본문 글꼴, 스타일 이름). 굵게는 제목에만 쓴다.
# 요청에 스타일이 없거나 모자라면 이 순서대로 추천안을 채운다
FONT_STYLES: dict[FontStyle, tuple[str, str, str]] = {
    "minimal_gothic": ("gmarket-sans", "nanum-square", "미니멀·모던 고딕"),
    "serif": ("bookk-myungjo", "bookk-myungjo", "세리프 감성"),
    "clean": ("paperlogy", "pretendard", "깔끔한 느낌"),
    "handwriting": ("ink-liquid", "nanum-brush-script", "손글씨 느낌"),
    "signature": ("mona12", "mona12", "시그니처"),
    "impact_sale": ("bithumb-gothic", "paperlogy", "임팩트 세일"),
    "rounded": (
        "school-safety-rounded-smile",
        "school-safety-rounded-smile",
        "부드러운 둥근 느낌",
    ),
}

# 짧은 변 대비 안전 여백
MARGIN = 0.07
# 짧은 변 대비 글자 크기
FONT_SIZES: dict[CopyRole, float] = {"title": 0.085, "subtitle": 0.04, "text": 0.03}
LINE_HEIGHTS: dict[CopyRole, float] = {"title": 1.15, "subtitle": 1.3, "text": 1.35}
# 다음 문구까지의 간격 (앞 문구 글자 크기 대비)
GAPS: dict[CopyRole, float] = {"title": 0.45, "subtitle": 0.9, "text": 0.9}
