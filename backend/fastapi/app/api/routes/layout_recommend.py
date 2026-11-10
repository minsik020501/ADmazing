"""이미지와 문구로 위치·글꼴·스타일 추천안을 만드는 라우터.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_layout_recommender
from app.schemas.layout_recommend_request import LayoutRecommendRequest
from app.schemas.layout_recommend_response import LayoutRecommendResponse
from app.services.layout_recommend_service import recommend_layouts
from app.services.template_layout_recommender import TemplateLayoutRecommender

router = APIRouter(tags=["layout"])


@router.post("/layout/recommend", response_model=LayoutRecommendResponse)
async def recommend_layout(
    req: LayoutRecommendRequest,
    layout_recommender: TemplateLayoutRecommender = Depends(get_layout_recommender),
):
    """이미지 한 장과 역할별 문구로 문구 상자 추천안을 3~5개 만든다.

    광고 레이아웃 템플릿 중 제품·얼굴을 가리지 않고 배경이 차분한 자리를 고르고,
    추천안마다 다른 글꼴 짝과 배색(제품색 강조, 톤온톤 등)을 쓴다.
    template_id를 보내면 그 레이아웃으로만 추천안을 만든다.
    응답은 docs/text_layer_spec.md의 추천안 형식이고, 문구는 요청한 그대로 들어간다.

    Args:
        req: 이미지, 역할별 문구(1~3개), 추천안 수, 강조색, 글꼴 스타일, 레이아웃 지정을
            담은 요청.
        layout_recommender: 의존성으로 주입되는 템플릿 추천기.

    Returns:
        LayoutRecommendResponse: 추천안 목록.
    """
    return await recommend_layouts(layout_recommender, req)
