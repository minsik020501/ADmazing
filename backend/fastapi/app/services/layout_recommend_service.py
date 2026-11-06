"""문구 배치 추천 서비스. 이미지를 읽고 템플릿 추천기를 스레드에서 실행한다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from fastapi.concurrency import run_in_threadpool

from app.schemas.layout_recommend_request import LayoutRecommendRequest
from app.schemas.layout_recommend_response import LayoutRecommendResponse
from app.services.template_layout_recommender import TemplateLayoutRecommender
from app.utils.image import decode_base64_image


async def recommend_layouts(
    recommender: TemplateLayoutRecommender, req: LayoutRecommendRequest
) -> LayoutRecommendResponse:
    """이미지와 역할별 문구로 위치·글꼴·색 추천안을 만든다.

    영역 찾기와 배치 계산은 CPU 작업이라 이벤트 루프를 막지 않도록 스레드에서 실행한다.

    Args:
        recommender: 템플릿 추천기.
        req: 이미지, 역할별 문구, 추천안 수를 담은 요청.

    Returns:
        LayoutRecommendResponse: 추천안 목록 (최대 req.num_proposals개).
    """
    image = decode_base64_image(req.image_base64)
    proposals = await run_in_threadpool(
        recommender.recommend, image, req.copies, req.num_proposals
    )
    return LayoutRecommendResponse(proposals=proposals)
