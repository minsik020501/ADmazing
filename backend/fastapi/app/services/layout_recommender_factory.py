"""문구 배치 추천기(템플릿 + 영역 찾기)를 만드는 팩토리.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from app.core.config import settings
from app.services.template_layout_recommender import TemplateLayoutRecommender


def create_layout_recommender() -> TemplateLayoutRecommender:
    """문구 배치 추천기를 만든다. LAYOUT_DETECT_SUBJECTS면 영역 찾기 모델을 이때 불러온다.

    Returns:
        TemplateLayoutRecommender: 템플릿 추천기.

    Raises:
        FileNotFoundError: 영역 찾기를 켰는데 모델 파일이 없을 때.
    """
    detector = None
    if settings.layout_detect_subjects:
        from app.services.subject_detector import SubjectDetector

        detector = SubjectDetector(
            settings.layout_salient_model_path, settings.layout_face_model_path
        )
    return TemplateLayoutRecommender(detector)
