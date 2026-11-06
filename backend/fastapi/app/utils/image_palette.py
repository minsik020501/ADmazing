"""이미지의 대표색(palette)을 뽑는 유틸리티.

에디터에서 글자색을 고를 때 이미지와 어울리는 기본색으로 쓴다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import math

from PIL import Image

from app.utils.color import to_oklch

# 돌려줄 대표색 수
PALETTE_SIZE = 5
# 색을 뽑기 전에 줄이는 크기 (긴 변). 대표색에는 세부가 필요 없다
_SAMPLE_SIDE = 128
# 처음에 나누는 색 수. 비슷한 색을 합친 뒤에도 PALETTE_SIZE개가 남도록 넉넉히 둔다
_QUANTIZE_COLORS = 16
# OKLCH 거리가 이보다 가까우면 같은 색으로 보고 하나만 남긴다
_MIN_DISTANCE = 0.08
# 이미지에서 차지하는 비율이 이보다 작은 색은 뺀다 (잡티)
_MIN_SHARE = 0.01


def extract_palette(image: Image.Image, size: int = PALETTE_SIZE) -> list[str]:
    """이미지에서 많이 쓰인 순서로 서로 다른 대표색을 뽑는다.

    Args:
        image: 원본 이미지.
        size: 뽑을 색 수.

    Returns:
        list[str]: #RRGGBB 목록 (많이 쓰인 순서, size개 이하).
    """
    sample = image.convert("RGB")
    sample.thumbnail((_SAMPLE_SIDE, _SAMPLE_SIDE))
    quantized = sample.quantize(
        colors=_QUANTIZE_COLORS, method=Image.Quantize.MEDIANCUT
    )
    flat = quantized.getpalette() or []
    counts = sorted(quantized.getcolors() or [], reverse=True)
    total = sample.width * sample.height

    picked: list[tuple[tuple[int, int, int], tuple[float, float, float]]] = []
    for count, index in counts:
        if count / total < _MIN_SHARE:
            break
        rgb = tuple(flat[index * 3 : index * 3 + 3])
        lab = _to_oklab(rgb)
        if all(math.dist(lab, other) >= _MIN_DISTANCE for _, other in picked):
            picked.append((rgb, lab))
        if len(picked) >= size:
            break
    return ["#" + "".join(f"{value:02X}" for value in rgb) for rgb, _ in picked]


def _to_oklab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """색 거리를 재기 위해 RGB를 OKLab 좌표로 바꾼다.

    Returns:
        tuple[float, float, float]: (L, a, b).
    """
    lightness, chroma, hue = to_oklch(rgb)
    return lightness, chroma * math.cos(hue), chroma * math.sin(hue)
