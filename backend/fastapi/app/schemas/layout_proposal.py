"""문구 배치 추천안 하나의 스키마 (에디터의 AI 추천안 칩).

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field

from app.core.layout_templates import FontStyle, TemplateId
from app.schemas.text_layer import TextLayer


class LayoutProposal(BaseModel):
    """칩 이름과 문구 상자 묶음. 칩을 누르면 이미지의 문구가 이 묶음으로 바뀐다."""

    label: str = Field(..., description="칩에 보여줄 짧은 이름")
    template_id: TemplateId = Field(..., description="이 추천안의 레이아웃 템플릿")
    style: FontStyle = Field(..., description="이 추천안의 글꼴 스타일")
    layers: list[TextLayer] = Field(..., description="뒤에 있을수록 위에 그려진다")
