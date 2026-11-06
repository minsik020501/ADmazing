"""색 변환(OKLCH)과 대비(WCAG) 계산 유틸리티.

OKLCH는 사람이 느끼는 밝기(L)·채도(C)·색조(h)를 나눠 다룰 수 있어, 색조를 지키면서 명도만
옮겨 대비를 맞추는 데 쓴다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import math

Oklch = tuple[float, float, float]
Rgb = tuple[float, float, float]


def to_oklch(rgb: Rgb) -> Oklch:
    """RGB(0~255)를 OKLCH로 바꾼다.

    Returns:
        Oklch: (L 0~1, C, h 라디안).
    """
    r, g, b = (_srgb_to_linear(v / 255) for v in rgb)
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return lightness, math.hypot(a, bb), math.atan2(bb, a)


def from_oklch(lightness: float, chroma: float, hue: float) -> str | None:
    """OKLCH를 #RRGGBB로 바꾼다.

    Returns:
        str | None: 색. sRGB 범위 밖이면 None.
    """
    a, bb = chroma * math.cos(hue), chroma * math.sin(hue)
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * bb) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * bb) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * bb) ** 3
    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    b = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    channels = [_linear_to_srgb(v) for v in (r, g, b)]
    if any(v < -0.001 or v > 1.001 for v in channels):
        return None
    return "#" + "".join(f"{round(min(max(v, 0), 1) * 255):02X}" for v in channels)


def contrast_ratio(hex_color: str, background: Rgb) -> float:
    """글자색과 배경색의 WCAG 대비비를 구한다.

    Args:
        hex_color: 글자색 #RRGGBB.
        background: 배경 RGB (0~255).

    Returns:
        float: 1~21. 클수록 읽기 쉽다.
    """
    first = relative_luminance(hex_to_rgb(hex_color))
    second = relative_luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def relative_luminance(rgb: Rgb) -> float:
    """WCAG 상대 휘도를 구한다.

    Returns:
        float: 0(검정)~1(흰색).
    """
    red, green, blue = (_srgb_to_linear(v / 255) for v in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """#RRGGBB를 RGB로 바꾼다.

    Returns:
        tuple[int, int, int]: RGB (0~255).
    """
    return tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))


def _srgb_to_linear(value: float) -> float:
    """sRGB 채널(0~1)을 선형 값으로 바꾼다.

    Returns:
        float: 선형 값.
    """
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(value: float) -> float:
    """선형 값을 sRGB 채널(0~1)로 바꾼다.

    Returns:
        float: sRGB 채널 값.
    """
    if value <= 0.0031308:
        return 12.92 * value
    return 1.055 * max(value, 0) ** (1 / 2.4) - 0.055
