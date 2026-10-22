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

# 비율 → (너비, 높이). 비율은 이름과 정확히 같게 하고, 총 픽셀 수는 SDXL 학습 해상도와
# 비슷한 약 1024x1024 수준으로 맞춘다 (픽셀 수가 크게 줄면 디테일이 떨어진다).
# 모두 8의 배수 (SDXL VAE가 1/8로 줄이므로 8의 배수여야 한다)
IMAGE_RESOLUTIONS: dict[ImageRatio, tuple[int, int]] = {
    ImageRatio.SQUARE: (1024, 1024),
    ImageRatio.LANDSCAPE_4_3: (1152, 864),
    ImageRatio.PORTRAIT_3_4: (864, 1152),
    ImageRatio.LANDSCAPE_16_9: (1280, 720),
    ImageRatio.PORTRAIT_9_16: (720, 1280),
    ImageRatio.LANDSCAPE_3_2: (1248, 832),
    ImageRatio.PORTRAIT_2_3: (832, 1248),
    ImageRatio.PORTRAIT_4_5: (896, 1120),
}
