"""문구 배치 추천 실패 예외.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

LAYOUT_RECOMMENDATION_FAILED_MESSAGE = (
    "문구 배치 추천에 실패했습니다. 잠시 후 다시 시도해 주세요."
)


class LayoutRecommendationError(Exception):
    """모델 출력을 읽을 수 없거나 쓸 수 있는 추천안이 없을 때 발생한다."""
