"""문구 배치 추천의 역할 배색.

    - 강조색: 제품 영역 안의 대표색 (채도·면적). 사람이 있으면 피부색 계열은 뺀다.
      제품이 무채색이면 강조색 없이 톤온톤으로 한다. 영역이 없으면(장면 사진) 이미지 전체에서 뽑는다
    - 중립색: 문구 블록 아래 배경의 색조로 살짝 물든 아주 어두운 색 또는 아주 밝은 색
    - 대비: 색조·채도는 지키고 OKLCH 명도만 옮겨 맞춘다 (title 3:1, 본문 4.5:1)
    - 추천안마다 다른 배색 방식을 쓰고, 한 추천안에는 최대 2색(중립 + 강조)만 쓴다

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import math

from PIL import Image, ImageStat

from app.core.copy_role import CopyRole
from app.schemas.text_layer import TextLayer
from app.schemas.text_layer_shadow import TextLayerShadow
from app.utils.color import Oklch, contrast_ratio, from_oklch, to_oklch

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
_DARK_FALLBACK = "#1C1C1C"
_LIGHT_FALLBACK = "#FFFFFF"


def accent_color(
    image: Image.Image, products: list[Box], has_face: bool, no_subjects: bool
) -> Oklch | None:
    """강조색을 뽑는다.

    Args:
        image: 원본 이미지.
        products: 제품 영역들.
        has_face: 사람 얼굴이 있는지. 있으면 피부색 계열은 후보에서 뺀다
            (제품 상자에 손이 같이 들어오기 때문이다).
        no_subjects: 제품·얼굴 영역이 아예 없는지 (장면 사진). 그러면 이미지 전체에서 뽑는다.

    Returns:
        Oklch | None: 강조색. 쓸 만한 색이 없으면 None (톤온톤).
    """
    if products:
        region_box = (
            min(b[0] for b in products),
            min(b[1] for b in products),
            max(b[2] for b in products),
            max(b[3] for b in products),
        )
    elif no_subjects:
        region_box = (0.0, 0.0, 1.0, 1.0)
    else:
        return None
    quantized = _crop(image, region_box).resize((64, 64)).quantize(colors=6)
    palette = quantized.getpalette()[: 6 * 3]
    best, best_score = None, 0.0
    for count, index in quantized.getcolors():
        lch = to_oklch(tuple(palette[index * 3 : index * 3 + 3]))
        if lch[1] < MIN_ACCENT_CHROMA or not 0.25 < lch[0] < 0.92:
            continue
        if has_face and _is_skin(lch):
            continue
        score = lch[1] * math.sqrt(count / (64 * 64))
        if score > best_score:
            best, best_score = lch, score
    return best


def apply_palette(
    layers: list[TextLayer],
    image: Image.Image,
    block: Box,
    scheme: str,
    accent: Oklch | None,
) -> str:
    """역할 배색을 적용한다.

    Args:
        layers: 한 추천안의 문구 상자들. color, shadow를 바꾼다.
        image: 원본 이미지.
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
        layer.color = fit_color(lch, background, target, dark)
        if busy > BUSY_SHADOW:
            layer.shadow = TextLayerShadow(
                color="#FFFFFF" if dark else "#000000",
                blur=0.012,
                offsetX=0,
                offsetY=0.002,
                opacity=0.35,
            )
    return scheme


def fit_color(lch: Oklch, background: tuple, target: float, dark: bool) -> str:
    """색조·채도를 지키면서 명도만 옮겨 배경 대비 target 이상인 색을 찾는다.

    sRGB 범위를 벗어나면 채도를 조금씩 줄인다.

    Args:
        lch: 시작 색.
        background: 배경 평균 RGB.
        target: 필요한 최소 대비.
        dark: True면 어두운 쪽으로, False면 밝은 쪽으로 옮긴다.

    Returns:
        str: #RRGGBB.
    """
    lightness, chroma, hue = lch
    step = -0.01 if dark else 0.01
    while 0.02 <= lightness <= 0.99:
        current, color = chroma, None
        while color is None and current >= 0:
            color = from_oklch(lightness, current, hue)
            current -= 0.01
        if color and contrast_ratio(color, background) >= target:
            return color
        lightness += step
    return _DARK_FALLBACK if dark else _LIGHT_FALLBACK


def busyness(image: Image.Image, block: Box) -> float:
    """블록 아래 배경이 얼마나 복잡한지(밝기 표준편차) 잰다.

    Returns:
        float: 0~255. 작을수록 차분하다.
    """
    return ImageStat.Stat(_crop(image, block).convert("L").resize((64, 64))).stddev[0]


def _is_skin(lch: Oklch) -> bool:
    """피부색 계열인지 대략 판단한다 (OKLCH 색조 20~80도, 채도 0.13 미만).

    Returns:
        bool: 피부색 계열이면 True.
    """
    hue = math.degrees(lch[2]) % 360
    return 20 <= hue <= 80 and lch[1] < 0.13


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
