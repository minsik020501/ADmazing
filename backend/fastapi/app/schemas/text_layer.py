"""에디터 문구 상자(텍스트 레이어) 스키마.

필드 이름과 범위, 기본값은 docs/text_layer_spec.md와 같다. FE가 그대로 쓰도록 camelCase로 둔다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.text_layer_background import TextLayerBackground
from app.schemas.text_layer_shadow import TextLayerShadow
from app.schemas.text_layer_stroke import TextLayerStroke


class TextLayer(BaseModel):
    """이미지 위에 그릴 문구 상자 하나. 위치와 크기는 이미지 대비 비율이다."""

    role: str | None = Field(None, max_length=30, description="title, subtitle, text")
    text: str = Field(..., min_length=1, max_length=200, description="표시할 문구")
    x: float = Field(0.5, ge=0, le=1, description="상자 가운데 가로 위치")
    y: float = Field(0.5, ge=0, le=1, description="상자 가운데 세로 위치")
    width: float | None = Field(None, ge=0.05, le=1, description="줄바꿈 폭")
    rotation: float = Field(0, ge=-180, le=180)
    curve: float = Field(0, ge=-100, le=100)
    fontId: str = Field("pretendard", description="글꼴 목록의 id")
    fontSize: float = Field(0.056, ge=0.01, le=0.4, description="이미지 세로 대비")
    bold: bool = False
    italic: bool = False
    strike: bool = False
    align: Literal["left", "center", "right"] = "center"
    lineHeight: float = Field(1.2, ge=0.8, le=2.5)
    color: str = Field("#FFFFFF", description="#RRGGBB")
    opacity: float = Field(1, ge=0, le=1)
    stroke: TextLayerStroke | None = None
    shadow: TextLayerShadow | None = None
    background: TextLayerBackground | None = None
