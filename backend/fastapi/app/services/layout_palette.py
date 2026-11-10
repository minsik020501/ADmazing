"""문구 배치 추천의 역할 배색.

    - 강조색: 문구 추천에서 OpenAI가 이미지를 보고 고른 색을 받는다 (명도는 여기서 다시 맞춘다).
      받지 못했거나 회색 계열이면 강조색 없이 톤온톤으로 한다
    - 중립색: 문구 블록 아래 배경의 색조로 살짝 물든 아주 어두운 색 또는 아주 밝은 색
    - 대비: 색조·채도는 지키고 OKLCH 명도만 옮겨 맞춘다 (title 3:1, 본문 4.5:1).
      평균색 하나가 아니라 줄마다 글자가 놓이는 영역의 픽셀을 모두 보고, 대비가 모자란
      픽셀이 10% 이하가 되게 한다. 어느 명도로도 안 되면 진한 그림자를 넣는다
    - 추천안마다 다른 배색 방식을 쓰고, 한 추천안에는 최대 2색(중립 + 강조)만 쓴다

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import numpy as np
from PIL import Image, ImageStat

from app.core.copy_role import CopyRole
from app.schemas.text_layer import TextLayer
from app.schemas.text_layer_shadow import TextLayerShadow
from app.utils.color import (
    Oklch,
    from_oklch,
    hex_to_rgb,
    relative_luminance,
    to_oklch,
)
from app.utils.text_measure import line_boxes

Box = tuple[float, float, float, float]

# 추천안 순서대로 쓰는 배색 방식
SCHEMES = ["accent_title", "tone_on_tone", "accent_text", "muted_accent"]
SCHEME_NAMES = {
    "accent_title": "제품색 강조",
    "tone_on_tone": "톤온톤",
    "accent_text": "본문 강조",
    "muted_accent": "차분한 제품색",
}
# 역할별 최소 대비 (WCAG: 큰 글자 3:1, 본문 4.5:1)
MIN_CONTRAST: dict[CopyRole, float] = {"title": 3.0, "subtitle": 4.5, "text": 4.5}
# 강조색으로 쓸 최소 채도 (OKLCH C)
MIN_ACCENT_CHROMA = 0.05
# 블록 아래 밝기 표준편차가 이보다 크면(복잡한 배경) 옅은 그림자를 넣는다
BUSY_SHADOW = 40
# 글자 아래 픽셀 중 대비가 모자란 픽셀이 이 비율 이하여야 읽힌다고 본다
MAX_FAIL_SHARE = 0.10
# 대비를 잴 휘도 지도의 긴 변 (px)
LUMINANCE_SIDE = 512
_DARK_FALLBACK = "#1C1C1C"
_LIGHT_FALLBACK = "#FFFFFF"


def accent_from_hex(color: str | None) -> Oklch | None:
    """요청으로 받은 강조색을 OKLCH로 바꾼다.

    Args:
        color: #RRGGBB (문구 추천에서 OpenAI가 고른 색). 없을 수 있다.

    Returns:
        Oklch | None: 강조색. 없거나 채도가 MIN_ACCENT_CHROMA보다 낮으면(회색 계열) None
            (톤온톤으로 바꾼다).
    """
    if not color:
        return None
    lch = to_oklch(hex_to_rgb(color))
    return lch if lch[1] >= MIN_ACCENT_CHROMA else None


def luminance_map(image: Image.Image) -> np.ndarray:
    """대비를 잴 픽셀별 WCAG 상대 휘도 지도를 만든다 (긴 변 LUMINANCE_SIDE로 줄인다).

    Returns:
        np.ndarray: (높이, 너비) 0~1.
    """
    small = image.convert("RGB")
    small.thumbnail((LUMINANCE_SIDE, LUMINANCE_SIDE))
    channels = np.asarray(small, dtype=np.float32) / 255
    linear = np.where(
        channels <= 0.04045, channels / 12.92, ((channels + 0.055) / 1.055) ** 2.4
    )
    return linear @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def text_background(
    luminance: np.ndarray, layer: TextLayer, aspect: float
) -> np.ndarray:
    """문구 상자에서 줄마다 글자가 놓이는 영역의 픽셀 휘도를 모은다.

    Args:
        luminance: luminance_map 결과.
        layer: 위치(x, y)가 정해진 문구 상자.
        aspect: 이미지 세로 / 가로.

    Returns:
        np.ndarray: 1차원 휘도 배열 (최소 1개).
    """
    height, width = luminance.shape
    boxes = line_boxes(
        layer.text,
        layer.fontSize,
        aspect,
        layer.width,
        layer.lineHeight,
        layer.align,
        (layer.x, layer.y),
    )
    parts = []
    for box in boxes:
        left = int(min(max(box[0], 0), 1) * width)
        top = int(min(max(box[1], 0), 1) * height)
        right = max(int(min(max(box[2], 0), 1) * width), left + 1)
        bottom = max(int(min(max(box[3], 0), 1) * height), top + 1)
        parts.append(luminance[top:bottom, left:right].ravel())
    pixels = np.concatenate(parts) if parts else np.empty(0, dtype=np.float32)
    if pixels.size == 0:
        cx = min(int(layer.x * width), width - 1)
        cy = min(int(layer.y * height), height - 1)
        pixels = luminance[cy : cy + 1, cx : cx + 1].ravel()
    return pixels


def fail_share(color: str, background: np.ndarray, target: float) -> float:
    """배경 픽셀 중 글자색과의 대비가 target보다 낮은 비율.

    Args:
        color: 글자색 #RRGGBB.
        background: text_background 결과.
        target: 필요한 최소 대비.

    Returns:
        float: 0~1.
    """
    text = relative_luminance(hex_to_rgb(color))
    ratio = (np.maximum(background, text) + 0.05) / (
        np.minimum(background, text) + 0.05
    )
    return float((ratio < target).mean())


def is_readable(background: np.ndarray, target: float) -> bool:
    """아주 어둡거나 아주 밝은 글자 중 하나라도 이 배경에서 읽히는지 확인한다.

    Returns:
        bool: 읽히는 글자색이 있으면 True.
    """
    return any(
        fail_share(color, background, target) <= MAX_FAIL_SHARE
        for color in (_DARK_FALLBACK, _LIGHT_FALLBACK)
    )


def apply_palette(
    layers: list[TextLayer],
    image: Image.Image,
    luminance: np.ndarray,
    block: Box,
    scheme: str,
    accent: Oklch | None,
) -> str:
    """역할 배색을 적용한다.

    Args:
        layers: 한 추천안의 문구 상자들. color, shadow를 바꾼다.
        image: 원본 이미지.
        luminance: luminance_map 결과.
        block: 문구 블록 영역.
        scheme: SCHEMES 중 하나.
        accent: 강조색. 없으면 톤온톤으로 바꾼다.

    Returns:
        str: 실제로 쓴 배색 방식.
    """
    region = _crop(image, block)
    background = tuple(ImageStat.Stat(region).mean[:3])
    busy = ImageStat.Stat(region.convert("L").resize((64, 64))).stddev[0]
    bg_l, bg_c, bg_h = to_oklch(background)
    dark = bg_l > 0.6
    neutral = (0.22 if dark else 0.97, min(bg_c, 0.03), bg_h)
    soft = (0.38 if dark else 0.9, min(bg_c, 0.025), bg_h)
    if accent is None:
        scheme = "tone_on_tone"
    aspect = image.height / image.width

    for layer in layers:
        role = layer.role
        target = MIN_CONTRAST[role]
        use_accent = (
            scheme in ("accent_title", "muted_accent") and role == "title"
        ) or (scheme == "accent_text" and role == "text")
        if use_accent:
            lch = accent
            if scheme == "muted_accent":
                lch = (lch[0], lch[1] * 0.55, lch[2])
        elif scheme == "tone_on_tone" and role != "title":
            lch = soft
        else:
            lch = neutral
        layer.color, readable = fit_color(
            lch, text_background(luminance, layer, aspect), target, dark
        )
        light_text = relative_luminance(hex_to_rgb(layer.color)) > 0.18
        if not readable:
            # 배경이 밝은 곳과 어두운 곳에 걸쳐 어떤 명도로도 안 되면 글자 둘레를 진하게 감싼다
            layer.shadow = TextLayerShadow(
                color="#000000" if light_text else "#FFFFFF",
                blur=0.02,
                offsetX=0,
                offsetY=0,
                opacity=0.65,
            )
        elif busy > BUSY_SHADOW:
            layer.shadow = TextLayerShadow(
                color="#000000" if light_text else "#FFFFFF",
                blur=0.012,
                offsetX=0,
                offsetY=0.002,
                opacity=0.35,
            )
    return scheme


def fit_color(
    lch: Oklch, background: np.ndarray, target: float, dark: bool
) -> tuple[str, bool]:
    """색조·채도를 지키면서 명도만 옮겨, 배경 픽셀 대부분과 대비 target 이상인 색을 찾는다.

    먼저 dark 쪽으로 옮겨 보고, 안 되면 반대쪽으로 옮긴다. sRGB 범위를 벗어나면 채도를
    조금씩 줄인다.

    Args:
        lch: 시작 색.
        background: text_background 결과 (글자 아래 픽셀 휘도).
        target: 필요한 최소 대비.
        dark: True면 어두운 쪽부터, False면 밝은 쪽부터 옮긴다.

    Returns:
        tuple[str, bool]: (#RRGGBB, 읽히는지). 어느 쪽으로도 안 되면 아주 어둡거나 아주
            밝은 색 중 대비가 모자란 픽셀이 적은 쪽과 False.
    """
    for toward_dark in (dark, not dark):
        color = _shift_lightness(lch, background, target, toward_dark)
        if color is not None:
            return color, True
    best = min(
        (_DARK_FALLBACK, _LIGHT_FALLBACK),
        key=lambda color: fail_share(color, background, target),
    )
    return best, False


def _shift_lightness(
    lch: Oklch, background: np.ndarray, target: float, toward_dark: bool
) -> str | None:
    """명도를 한쪽으로 옮기며 읽히는 첫 색을 찾는다.

    Returns:
        str | None: #RRGGBB. 끝까지 옮겨도 안 되면 None.
    """
    lightness, chroma, hue = lch
    step = -0.01 if toward_dark else 0.01
    while 0.02 <= lightness <= 0.99:
        current, color = chroma, None
        while color is None and current >= 0:
            color = from_oklch(lightness, current, hue)
            current -= 0.01
        if color and fail_share(color, background, target) <= MAX_FAIL_SHARE:
            return color
        lightness += step
    return None


def busyness(image: Image.Image, block: Box) -> float:
    """블록 아래 배경이 얼마나 복잡한지(밝기 표준편차) 잰다.

    Returns:
        float: 0~255. 작을수록 차분하다.
    """
    return ImageStat.Stat(_crop(image, block).convert("L").resize((64, 64))).stddev[0]


def _crop(image: Image.Image, box: Box) -> Image.Image:
    """비율 상자로 이미지를 자른다. 너무 작으면 1px은 남긴다.

    Returns:
        Image.Image: 자른 RGB 이미지.
    """
    width, height = image.size
    left = int(min(max(box[0], 0), 1) * width)
    top = int(min(max(box[1], 0), 1) * height)
    right = max(int(min(max(box[2], 0), 1) * width), left + 1)
    bottom = max(int(min(max(box[3], 0), 1) * height), top + 1)
    return image.convert("RGB").crop((left, top, right, bottom))
