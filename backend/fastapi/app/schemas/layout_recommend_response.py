"""문구 배치 추천 응답 스키마 (docs/text_layer_spec.md의 추천안 형식).

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field

from app.schemas.layout_proposal import LayoutProposal


class LayoutRecommendResponse(BaseModel):
    """이미지 한 장에 대한 추천안 목록."""

    proposals: list[LayoutProposal] = Field(..., description="추천안 (최대 5개)")
