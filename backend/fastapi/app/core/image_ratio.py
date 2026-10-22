"""이미지 비율과 비율별 생성 해상도 상수.

생성일자: 2026-10-22
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from enum import StrEnum


class ImageRatio(StrEnum):
    """요청에서 선택할 수 있는 이미지 비율 (가로:세로)."""

    SQUARE = "1:1"
    LANDSCAPE_4_3 = "4:3"
    PORTRAIT_3_4 = "3:4"
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"
    LANDSCAPE_3_2 = "3:2"
    PORTRAIT_2_3 = "2:3"
    PORTRAIT_4_5 = "4:5"


DEFAULT_IMAGE_RATIO = ImageRatio.SQUARE

# 비율 → (너비, 높이). SDXL 학습 해상도(버킷)를 그대로 써서 총 픽셀 수를 1024x1024 수준으로 맞춘다.
# 버킷은 64의 배수라 비율이 정확히 일치하지는 않는다 (예: 16:9 → 1344x768 = 1.75:1)
IMAGE_RESOLUTIONS: dict[ImageRatio, tuple[int, int]] = {
    ImageRatio.SQUARE: (1024, 1024),
    ImageRatio.LANDSCAPE_4_3: (1152, 896),
    ImageRatio.PORTRAIT_3_4: (896, 1152),
    ImageRatio.LANDSCAPE_16_9: (1344, 768),
    ImageRatio.PORTRAIT_9_16: (768, 1344),
    ImageRatio.LANDSCAPE_3_2: (1216, 832),
    ImageRatio.PORTRAIT_2_3: (832, 1216),
    ImageRatio.PORTRAIT_4_5: (896, 1088),
}
