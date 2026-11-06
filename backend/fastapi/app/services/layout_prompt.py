"""문구 배치 추천 모델(Qwen3-VL)에 보낼 지시문을 만든다.

모델은 결정해야 할 값만 압축 형식으로 내고, 서버가 문구 상자(TextLayer)로 펼친다.
Step 3 양자화 비교 스크립트도 이 모듈을 그대로 쓴다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import json

from app.core.copy_role import CopyRole
from app.schemas.layout_copy import LayoutCopy

# 역할별 글자 크기 가이드 (이미지 세로 대비)
ROLE_SIZE_GUIDE: dict[CopyRole, tuple[float, float]] = {
    "title": (0.07, 0.14),
    "subtitle": (0.04, 0.07),
    "text": (0.03, 0.05),
}

EFFECTS = ("none", "stroke", "shadow", "background")

SYSTEM_PROMPT = (
    "You are an expert advertising layout designer. Given an ad image and Korean "
    "ad copy, you decide where each line of copy goes and how it is styled so the "
    "ad looks professional and the copy is easy to read.\n"
    "You answer with JSON only, no explanations and no code fences."
)

# 출력 형식 예시에 넣는 역할별 값. 모델이 예시를 그대로 따라 하지 않도록 첫 추천안 하나만 보여준다
_EXAMPLE_LAYERS: dict[CopyRole, dict] = {
    "title": {"y": 0.14, "font": "black-han-sans", "effect": "stroke"},
    "subtitle": {"y": 0.24, "font": "pretendard", "effect": "shadow"},
    "text": {"y": 0.88, "font": "pretendard", "effect": "background"},
}


def size_guide(role: CopyRole, width: int, height: int) -> tuple[float, float]:
    """이미지 비율에 맞춘 역할별 글자 크기 범위(이미지 세로 대비)를 구한다.

    크기가 세로 대비라서 세로로 긴 이미지(9:16 등)에서는 같은 값도 가로로 훨씬 넓어진다.
    그래서 세로가 가로보다 길면 가로/세로 비율만큼 줄인다.

    Returns:
        tuple[float, float]: (최소, 최대) 글자 크기.
    """
    scale = min(1.0, width / height)
    low, high = ROLE_SIZE_GUIDE[role]
    return round(low * scale, 3), round(high * scale, 3)


def _example(copies: list[LayoutCopy], width: int, height: int) -> dict:
    """요청한 역할이 모두 들어간 추천안 하나짜리 출력 예시를 만든다.

    Returns:
        dict: {"proposals": [{"label", "layers"}]} 형태의 예시.
    """
    layers = []
    for copy in copies:
        low, high = size_guide(copy.role, width, height)
        example = _EXAMPLE_LAYERS[copy.role]
        layers.append(
            {
                "role": copy.role,
                "x": 0.5,
                "y": example["y"],
                "size": round((low + high) / 2, 3),
                "font": example["font"],
                "color": "#FFFFFF",
                "align": "center",
                "effect": example["effect"],
                "effect_color": "#000000",
            }
        )
    return {"proposals": [{"label": "강렬한 상단 헤드라인", "layers": layers}]}


def build_user_prompt(
    copies: list[LayoutCopy],
    fonts: tuple[dict, ...],
    width: int,
    height: int,
    num_proposals: int,
) -> str:
    """문구, 글꼴 목록, 좌표 규칙, 출력 형식을 담은 사용자 지시문을 만든다.

    Args:
        copies: 배치할 역할별 문구.
        fonts: 고를 수 있는 글꼴 목록 ({"id", "category", "mood"}).
        width: 원본 이미지 너비 (px).
        height: 원본 이미지 높이 (px).
        num_proposals: 만들 추천안 수.

    Returns:
        str: 모델에 이미지와 함께 보낼 지시문.
    """
    copy_lines = [
        f'- {copy.role}: "{copy.text}" ({len(copy.text)} characters)' for copy in copies
    ]
    font_lines = [
        f"- {font['id']} ({font['category']}): {font['mood']}" for font in fonts
    ]
    size_lines = [
        "- {}: {}~{}".format(copy.role, *size_guide(copy.role, width, height))
        for copy in copies
    ]
    roles = ", ".join(copy.role for copy in copies)
    return "\n".join(
        [
            f"The image is {width}x{height} pixels (width x height).",
            "",
            "Ad copy to place (use every line exactly once per proposal; "
            "do not change the text):",
            *copy_lines,
            "",
            "Fonts you can use (id (category): mood):",
            *font_lines,
            "",
            "Coordinates:",
            "- x, y: center of the text box as a ratio of the image. "
            "(0, 0) is top-left, (1, 1) is bottom-right.",
            "- x is always the CENTER, even for left or right aligned text. A box "
            "on the left side of the image has x around 0.3, not its left edge.",
            "- size: font size as a ratio of the image HEIGHT. Recommended ranges:",
            *size_lines,
            "",
            "Rules:",
            "- Never cover the main product or subject. Put copy on empty or calm "
            "areas such as the sky, a plain wall or the table surface.",
            "- Keep every text box fully inside the image with a small margin. "
            "Consider how wide the text will be at the chosen size.",
            "- Use dark text on bright areas and bright text on dark areas.",
            "- If the area behind the text is busy, use an effect: stroke, shadow "
            "or background (a box behind the text).",
            "- Keep a clear hierarchy: title is the biggest, then subtitle, then text.",
            "- Lines of the same proposal must not overlap each other.",
            f"- Make {num_proposals} proposals that are clearly different from each "
            "other: vary the position (top, bottom, left, right, center) and the "
            "font category.",
            "- label: a short Korean name for the proposal (at most 12 characters).",
            "",
            "Output minified JSON on a single line (no indentation, no line breaks) "
            "with this structure:",
            json.dumps(_example(copies, width, height), ensure_ascii=False),
            f"Every proposal must have exactly {len(copies)} layers, one for each "
            f"role: {roles}. Do not skip any role.",
            f"effect is one of: {', '.join(EFFECTS)}. "
            "effect_color is the color of the effect (#RRGGBB).",
            "align is one of: left, center, right.",
        ]
    )
