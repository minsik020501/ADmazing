"""라우터에서 사용하는 의존성 주입 함수.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from fastapi import Request

from app.services.copy_recommender import CopyRecommender
from app.services.generation_job_store import GenerationJobStore
from app.services.template_layout_recommender import TemplateLayoutRecommender
from app.services.image_generator import ImageGenerator


def get_image_generator(request: Request) -> ImageGenerator:
    """서버 시작 시 로드된 이미지 생성기를 반환한다.

    Returns:
        ImageGenerator: app.state에 저장된 이미지 생성기.
    """
    return request.app.state.image_generator


def get_job_store(request: Request) -> GenerationJobStore:
    """서버 시작 시 만든 이미지 생성 작업 저장소를 반환한다.

    Returns:
        GenerationJobStore: app.state에 저장된 작업 저장소.
    """
    return request.app.state.job_store


def get_copy_recommender(request: Request) -> CopyRecommender:
    """서버 시작 시 만든 문구 추천기를 반환한다.

    Returns:
        CopyRecommender: app.state에 저장된 문구 추천기.
    """
    return request.app.state.copy_recommender


def get_layout_recommender(request: Request) -> TemplateLayoutRecommender:
    """서버 시작 시 만든 문구 배치 추천기를 반환한다.

    Returns:
        TemplateLayoutRecommender: app.state에 저장된 문구 배치 추천기.
    """
    return request.app.state.layout_recommender
