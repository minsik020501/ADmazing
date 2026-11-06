"""설정에 맞는 문구 배치 추천기를 만드는 팩토리.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from app.core.config import settings
from app.services.layout_recommender import LayoutRecommender
from app.services.mock_layout_recommender import MockLayoutRecommender


def create_layout_recommender() -> LayoutRecommender:
    """LAYOUT_RECOMMENDER 설정에 맞는 추천기를 만든다. qwen이면 모델을 이때 불러온다.

    Returns:
        LayoutRecommender: mock이면 고정 템플릿 추천기, qwen이면 Qwen3-VL 추천기.
    """
    if settings.layout_recommender == "qwen":
        # torch, transformers는 INSTALL_ML=true 빌드에만 있으므로 필요할 때만 import한다
        from app.services.qwen_layout_recommender import QwenLayoutRecommender

        return QwenLayoutRecommender()
    return MockLayoutRecommender()
