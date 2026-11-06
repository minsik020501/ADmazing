"""이미지와 문구로 위치·글꼴·스타일 추천안을 만드는 라우터.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_layout_recommender
from app.schemas.error_response import ErrorResponse
from app.schemas.layout_recommend_request import LayoutRecommendRequest
from app.schemas.layout_recommend_response import LayoutRecommendResponse
from app.services.ad_image_service import GPU_OUT_OF_MEMORY_MESSAGE
from app.services.gpu_out_of_memory_error import GpuOutOfMemoryError
from app.services.layout_recommend_service import recommend_layouts
from app.services.layout_recommendation_error import (
    LAYOUT_RECOMMENDATION_FAILED_MESSAGE,
    LayoutRecommendationError,
)
from app.services.layout_recommender import LayoutRecommender

logger = logging.getLogger(__name__)

router = APIRouter(tags=["layout"])


@router.post(
    "/layout/recommend",
    response_model=LayoutRecommendResponse,
    responses={
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "모델 출력을 읽지 못해 쓸 수 있는 추천안이 없음",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "추천 중 GPU 메모리 부족",
        },
    },
)
async def recommend_layout(
    req: LayoutRecommendRequest,
    layout_recommender: LayoutRecommender = Depends(get_layout_recommender),
):
    """이미지 한 장과 역할별 문구로 문구 상자 추천안을 최대 5개 만든다.

    응답은 docs/text_layer_spec.md의 추천안 형식이다. 문구는 요청한 그대로 들어간다.
    이미지 생성과 같은 GPU를 쓰므로 이미지 생성 중이면 끝날 때까지 기다린다.

    Args:
        req: 이미지, 역할별 문구(1~3개), 추천안 수를 담은 요청.
        layout_recommender: 의존성으로 주입되는 문구 배치 추천기.

    Returns:
        LayoutRecommendResponse: 추천안 목록.

    Raises:
        HTTPException: 쓸 수 있는 추천안이 없을 때 (502), GPU 메모리가 부족할 때 (503).
    """
    try:
        return await recommend_layouts(layout_recommender, req)
    except LayoutRecommendationError as error:
        logger.warning("문구 배치 추천 실패: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=LAYOUT_RECOMMENDATION_FAILED_MESSAGE,
        )
    except GpuOutOfMemoryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=GPU_OUT_OF_MEMORY_MESSAGE,
        )
