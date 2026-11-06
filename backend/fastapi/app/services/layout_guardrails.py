"""문구 배치 모델의 압축 출력을 검사·보정해 문구 상자(TextLayer)로 펼친다.

모델 출력을 그대로 믿지 않고 아래 순서로 처리한다. 고친 내용은 fixes로 돌려줘
로그와 Step 3 지표(가드레일 전후 비교)에 쓴다.

1. 모르는 글꼴, 형식이 틀린 색, 범위 밖 숫자를 기본값·범위 안으로 맞춘다
2. 글꼴 크기와 글자 수로 상자 크기를 어림해, 너무 넓으면 줄바꿈 폭을 정하고
   이미지 밖으로 나가지 않게 옮긴다 (세로가 넘치면 글꼴 크기를 줄인다)
3. 상자 뒤 배경과 글자색의 대비가 낮고 효과가 없으면 외곽선을 붙인다
4. 요청 문구를 넣고, 모델이 빠뜨린 역할은 기본 위치에 채운다

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import math
import re
import unicodedata

from PIL import Image, ImageStat

from app.core.copy_role import CopyRole
from app.core.fonts import DEFAULT_FONT_ID, font_ids
from app.schemas.layout_copy import LayoutCopy
from app.schemas.layout_proposal import LayoutProposal
from app.schemas.text_layer import TextLayer
from app.schemas.text_layer_background import TextLayerBackground
from app.schemas.text_layer_shadow import TextLayerShadow
from app.schemas.text_layer_stroke import TextLayerStroke
from app.services.layout_prompt import EFFECTS, size_guide

# 역할별 기본 글꼴 (모르는 글꼴 id가 왔을 때)
ROLE_DEFAULT_FONT: dict[CopyRole, str] = {
    "title": "gmarket-sans",
    "subtitle": DEFAULT_FONT_ID,
    "text": DEFAULT_FONT_ID,
}
# 모델이 역할을 빠뜨렸을 때 쓰는 기본 가운데 위치 (x, y)
ROLE_DEFAULT_POSITION: dict[CopyRole, tuple[float, float]] = {
    "title": (0.5, 0.15),
    "subtitle": (0.5, 0.27),
    "text": (0.5, 0.86),
}
# 상자와 이미지 가장자리 사이에 남길 여백 (이미지 대비)
EDGE_MARGIN = 0.03
# 한 줄이 이보다 넓으면 이 폭(이미지 가로 대비)에서 줄을 바꾼다
WRAP_WIDTH = 0.8
# 글자색과 배경의 WCAG 대비비가 이보다 낮으면 효과를 붙인다
MIN_CONTRAST = 3.0
# 글꼴 크기 범위 (docs/text_layer_spec.md)
_FONT_SIZE_RANGE = (0.01, 0.4)
_LINE_HEIGHT = 1.2
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_MAX_LABEL_LENGTH = 20
# 대비를 잴 때 이미지를 줄이는 크기 (속도용)
_CONTRAST_SAMPLE_SIDE = 256


def build_proposals(
    raw_proposals: list[dict],
    copies: list[LayoutCopy],
    image: Image.Image,
    num_proposals: int,
) -> tuple[list[LayoutProposal], list[str]]:
    """모델의 압축 추천안을 검사·보정해 문구 상자 추천안으로 만든다.

    Args:
        raw_proposals: 모델 출력에서 꺼낸 추천안 목록 (layout_output_parser).
        copies: 요청한 역할별 문구.
        image: 원본 이미지. 비율과 배경 밝기를 보는 데 쓴다.
        num_proposals: 돌려줄 최대 추천안 수.

    Returns:
        tuple[list[LayoutProposal], list[str]]: 추천안 목록과 고친 내용 목록.
            고친 내용은 "p1.title: unknown font 'abc'"처럼 추천안 순번과 역할을 붙인다.
    """
    sample = image.convert("RGB")
    sample.thumbnail((_CONTRAST_SAMPLE_SIDE, _CONTRAST_SAMPLE_SIDE))
    aspect = image.height / image.width
    proposals: list[LayoutProposal] = []
    fixes: list[str] = []
    for index, raw in enumerate(raw_proposals[:num_proposals], start=1):
        prefix = f"p{index}"
        raw_layers = raw.get("layers")
        if not isinstance(raw_layers, list):
            fixes.append(f"{prefix}: layers missing, dropped")
            continue
        by_role = _layers_by_role(raw_layers, prefix, fixes)
        layers = []
        for copy in copies:
            raw_layer = by_role.get(copy.role)
            if raw_layer is None:
                fixes.append(f"{prefix}.{copy.role}: missing, default position")
                raw_layer = {}
            layers.append(
                _build_layer(
                    raw_layer, copy, aspect, sample, f"{prefix}.{copy.role}", fixes
                )
            )
        label = raw.get("label")
        if not isinstance(label, str) or not label.strip():
            label = f"추천안 {index}"
            fixes.append(f"{prefix}: label missing")
        proposals.append(
            LayoutProposal(label=label.strip()[:_MAX_LABEL_LENGTH], layers=layers)
        )
    return proposals, fixes


def _layers_by_role(raw_layers: list, prefix: str, fixes: list[str]) -> dict[str, dict]:
    """모델 출력 레이어를 역할별로 모은다. 같은 역할이 여러 번이면 첫 번째만 쓴다.

    Returns:
        dict[str, dict]: 역할 → 레이어 dict.
    """
    by_role: dict[str, dict] = {}
    for raw_layer in raw_layers:
        if not isinstance(raw_layer, dict):
            continue
        role = raw_layer.get("role")
        if role in by_role:
            fixes.append(f"{prefix}.{role}: duplicate role, dropped")
            continue
        by_role[role] = raw_layer
    return by_role


def _build_layer(
    raw: dict,
    copy: LayoutCopy,
    aspect: float,
    sample: Image.Image,
    prefix: str,
    fixes: list[str],
) -> TextLayer:
    """압축 레이어 하나를 검사·보정해 문구 상자로 펼친다.

    Args:
        raw: 모델 출력 레이어 ({role, x, y, size, font, color, align, effect, effect_color}).
        copy: 이 역할의 요청 문구.
        aspect: 이미지 세로 / 가로.
        sample: 대비 계산용으로 줄인 RGB 이미지.
        prefix: 고친 내용 앞에 붙일 위치 표시.
        fixes: 고친 내용을 추가할 목록.

    Returns:
        TextLayer: 문구 상자.
    """
    role = copy.role
    default_x, default_y = ROLE_DEFAULT_POSITION[role]
    default_size = sum(size_guide(role, sample.width, sample.height)) / 2

    font = raw.get("font")
    if font not in font_ids():
        if raw:
            fixes.append(f"{prefix}: unknown font {font!r}")
        font = ROLE_DEFAULT_FONT[role]
    color = _color(raw.get("color"), "#FFFFFF", f"{prefix}.color", fixes, bool(raw))
    align = raw.get("align")
    if align not in ("left", "center", "right"):
        if raw:
            fixes.append(f"{prefix}: invalid align {align!r}")
        align = "center"
    effect = raw.get("effect")
    if effect not in EFFECTS:
        if raw and effect is not None:
            fixes.append(f"{prefix}: invalid effect {effect!r}")
        effect = "none"
    effect_color = _color(
        raw.get("effect_color"),
        _contrasting(color),
        f"{prefix}.effect_color",
        fixes,
        False,
    )

    size = _number(
        raw.get("size"),
        default_size,
        _FONT_SIZE_RANGE,
        f"{prefix}.size",
        fixes,
        bool(raw),
    )
    x = _number(raw.get("x"), default_x, (0, 1), f"{prefix}.x", fixes, bool(raw))
    y = _number(raw.get("y"), default_y, (0, 1), f"{prefix}.y", fixes, bool(raw))

    x, y, size, wrap = _fit_inside(copy.text, x, y, size, aspect, prefix, fixes)

    if effect == "none":
        box = _box(copy.text, x, y, size, aspect, wrap)
        ratio = _contrast_ratio(color, _mean_color(sample, box))
        if ratio < MIN_CONTRAST:
            fixes.append(f"{prefix}: low contrast {ratio:.1f}, stroke added")
            effect = "stroke"
            effect_color = _contrasting(color)

    return TextLayer(
        role=role,
        text=copy.text,
        x=round(x, 4),
        y=round(y, 4),
        width=wrap,
        fontId=font,
        fontSize=round(size, 4),
        align=align,
        lineHeight=_LINE_HEIGHT,
        color=color,
        stroke=TextLayerStroke(color=effect_color) if effect == "stroke" else None,
        shadow=TextLayerShadow(color=effect_color) if effect == "shadow" else None,
        background=(
            TextLayerBackground(color=effect_color) if effect == "background" else None
        ),
    )


def _number(
    value,
    default: float,
    bounds: tuple[float, float],
    name: str,
    fixes: list[str],
    report: bool,
) -> float:
    """숫자를 읽어 범위 안으로 맞춘다. 숫자가 아니면 기본값을 쓴다.

    Returns:
        float: 범위 안의 숫자.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if report:
            fixes.append(f"{name}: not a number {value!r}")
        return default
    low, high = bounds
    if not low <= value <= high:
        fixes.append(f"{name}: {value} out of range")
        return min(max(float(value), low), high)
    return float(value)


def _color(value, default: str, name: str, fixes: list[str], report: bool) -> str:
    """#RRGGBB 색을 읽는다. 형식이 틀리면 기본값을 쓴다.

    Returns:
        str: 대문자 #RRGGBB.
    """
    if isinstance(value, str) and _HEX_COLOR.match(value):
        return value.upper()
    if report:
        fixes.append(f"{name}: invalid color {value!r}")
    return default


def _fit_inside(
    text: str,
    x: float,
    y: float,
    size: float,
    aspect: float,
    prefix: str,
    fixes: list[str],
) -> tuple[float, float, float, float | None]:
    """상자가 이미지(여백 포함) 안에 들어가도록 줄바꿈 폭을 정하고 가운데 위치를 옮긴다.

    한 줄로 WRAP_WIDTH보다 넓으면 글자를 줄이지 않고 줄바꿈 폭(width)을 정해 여러 줄로 만든다.
    줄바꿈 후에도 세로가 넘치면 그때 글꼴 크기를 줄인다.

    Returns:
        tuple[float, float, float, float | None]: 보정한 (x, y, 글꼴 크기, 줄바꿈 폭).
            줄바꿈 폭이 None이면 한 줄(또는 \\n에서만 줄바꿈)이다.
    """
    usable = 1 - 2 * EDGE_MARGIN
    wrap = None
    width, height = _box_size(text, size, aspect, wrap)
    if width > WRAP_WIDTH:
        wrap = WRAP_WIDTH
        width, height = _box_size(text, size, aspect, wrap)
        fixes.append(f"{prefix}: too wide, wrapped at width {wrap}")
    if height > usable:
        size = max(size * usable / height, _FONT_SIZE_RANGE[0])
        width, height = _box_size(text, size, aspect, wrap)
        fixes.append(f"{prefix}: too tall, size reduced to {size:.3f}")

    fitted_x = _clamp_center(x, width)
    fitted_y = _clamp_center(y, height)
    if abs(fitted_x - x) > 1e-6 or abs(fitted_y - y) > 1e-6:
        fixes.append(
            f"{prefix}: outside image, moved ({x:.2f}, {y:.2f}) -> "
            f"({fitted_x:.2f}, {fitted_y:.2f})"
        )
    return fitted_x, fitted_y, size, wrap


def _clamp_center(center: float, length: float) -> float:
    """길이가 length인 상자의 가운데를 여백 안쪽 범위로 맞춘다.

    Returns:
        float: 보정한 가운데 위치.
    """
    low = EDGE_MARGIN + length / 2
    high = 1 - EDGE_MARGIN - length / 2
    if low > high:
        return 0.5
    return min(max(center, low), high)


def _box_size(
    text: str, size: float, aspect: float, wrap: float | None = None
) -> tuple[float, float]:
    """글자 수와 글꼴 크기로 상자 크기를 어림한다 (실제 글꼴 폭은 글꼴마다 다르다).

    Args:
        text: 문구 (줄바꿈 \\n 포함 가능).
        size: 글꼴 크기 (이미지 세로 대비).
        aspect: 이미지 세로 / 가로.
        wrap: 줄바꿈 폭 (이미지 가로 대비). None이면 \\n에서만 줄을 바꾼다.

    Returns:
        tuple[float, float]: (이미지 가로 대비 폭, 이미지 세로 대비 높이).
    """
    widths = [
        sum(_char_em(char) for char in line) * size * aspect
        for line in text.split("\n")
    ]
    if wrap is None:
        return max(widths), len(widths) * size * _LINE_HEIGHT
    lines = sum(max(1, math.ceil(width / wrap)) for width in widths)
    return min(max(widths), wrap), lines * size * _LINE_HEIGHT


def _char_em(char: str) -> float:
    """글자 하나의 폭을 글꼴 크기(em) 대비로 어림한다.

    Returns:
        float: 한글·한자 등 전각 1.0, 공백 0.3, 영문 대문자 0.65, 그 밖의 반각 0.55.
    """
    if char.isspace():
        return 0.3
    if unicodedata.east_asian_width(char) in ("W", "F"):
        return 1.0
    if char.isupper():
        return 0.65
    return 0.55


def _box(
    text: str, x: float, y: float, size: float, aspect: float, wrap: float | None
) -> tuple[float, float, float, float]:
    """상자의 (왼쪽, 위, 오른쪽, 아래)를 이미지 대비 비율로 구한다.

    Returns:
        tuple[float, float, float, float]: 0~1로 자른 상자 좌표.
    """
    width, height = _box_size(text, size, aspect, wrap)
    return (
        max(x - width / 2, 0),
        max(y - height / 2, 0),
        min(x + width / 2, 1),
        min(y + height / 2, 1),
    )


def _mean_color(
    sample: Image.Image, box: tuple[float, float, float, float]
) -> tuple[float, float, float]:
    """상자 영역의 평균 색을 구한다.

    Returns:
        tuple[float, float, float]: 평균 RGB (0~255).
    """
    left, top, right, bottom = box
    width, height = sample.size
    region = sample.crop(
        (
            int(left * width),
            int(top * height),
            max(int(right * width), int(left * width) + 1),
            max(int(bottom * height), int(top * height) + 1),
        )
    )
    return tuple(ImageStat.Stat(region).mean[:3])


def _contrast_ratio(hex_color: str, rgb: tuple[float, float, float]) -> float:
    """글자색과 배경색의 WCAG 대비비를 구한다.

    Returns:
        float: 1~21. 클수록 읽기 쉽다.
    """
    first = _luminance(_hex_to_rgb(hex_color))
    second = _luminance(rgb)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _contrasting(hex_color: str) -> str:
    """글자색과 대비되는 효과 색(검정 또는 흰색)을 고른다.

    Returns:
        str: 밝은 글자면 "#000000", 어두운 글자면 "#FFFFFF".
    """
    return "#000000" if _luminance(_hex_to_rgb(hex_color)) > 0.4 else "#FFFFFF"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """#RRGGBB를 RGB로 바꾼다.

    Returns:
        tuple[int, int, int]: RGB (0~255).
    """
    return tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))


def _luminance(rgb: tuple[float, float, float]) -> float:
    """WCAG 상대 휘도를 구한다.

    Returns:
        float: 0(검정)~1(흰색).
    """

    def channel(value: float) -> float:
        """sRGB 채널 하나를 선형 값으로 바꾼다."""
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(value) for value in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue
