"""이미지 한 장의 광고 문구를 다시 추천하는 라우터.

이미지 생성 작업에서 문구 추천이 실패했을 때(copies_error) 다시 시도하는 데 쓴다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_copy_recommender
from app.schemas.copy_recommend_request import CopyRecommendRequest
from app.schemas.error_response import ErrorResponse
from app.schemas.image_copies import ImageCopies
from app.services.copy_recommend_service import recommend_copies
from app.services.copy_recommendation_error import (
    COPY_RECOMMENDATION_FAILED_MESSAGE,
    CopyRecommendationError,
)
from app.services.copy_recommender import CopyRecommender

logger = logging.getLogger(__name__)

router = APIRouter(tags=["copy"])


@router.post(
    "/copy/recommend",
    response_model=ImageCopies,
    responses={
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "OpenAI 호출 실패, 시간 초과 등으로 문구 추천 실패",
        },
    },
)
async def recommend_copy(
    req: CopyRecommendRequest,
    copy_recommender: CopyRecommender = Depends(get_copy_recommender),
):
    """이미지 한 장에 어울리는 title, subtitle, text 문구를 역할마다 최대 5개 추천한다.

    역할마다 사용자 문장을 그대로 앞에 두고, 남는 자리를 AI 문구로 채운다.

    Args:
        req: 이미지, 한국어 프롬프트, 사용자 문장을 담은 요청.
        copy_recommender: 의존성으로 주입되는 문구 추천기.

    Returns:
        ImageCopies: 역할별 추천 문구.

    Raises:
        HTTPException: 문구 추천에 실패했을 때 (502).
    """
    try:
        return await recommend_copies(
            copy_recommender, req.image_base64, req.prompt, req.user_copies
        )
    except CopyRecommendationError as error:
        logger.warning("문구 추천 실패: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=COPY_RECOMMENDATION_FAILED_MESSAGE,
        )
