"""설정에 맞는 문구 추천기를 만드는 팩토리.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from app.core.config import settings
from app.services.copy_recommender import CopyRecommender
from app.services.mock_copy_recommender import MockCopyRecommender
from app.services.openai_copy_recommender import OpenAICopyRecommender


def create_copy_recommender() -> CopyRecommender:
    """COPY_RECOMMENDER 설정에 맞는 문구 추천기를 만든다.

    Returns:
        CopyRecommender: mock이면 고정 문구 추천기, openai면 OpenAI 문구 추천기.
    """
    if settings.copy_recommender == "mock":
        return MockCopyRecommender()
    return OpenAICopyRecommender()
