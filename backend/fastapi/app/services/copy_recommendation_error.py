"""문구 추천 실패 예외.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

COPY_RECOMMENDATION_FAILED_MESSAGE = (
    "문구 추천에 실패했습니다. 잠시 후 다시 시도해 주세요."
)


class CopyRecommendationError(Exception):
    """OpenAI 호출 실패, 응답 형식 오류 등으로 문구를 추천하지 못했을 때 발생한다."""
