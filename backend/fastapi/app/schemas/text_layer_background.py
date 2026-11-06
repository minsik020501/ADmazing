"""문구 상자 배경 상자 스키마 (docs/text_layer_spec.md의 background).

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field


class TextLayerBackground(BaseModel):
    """글자 뒤 배경 상자. 여백과 둥글기는 이미지 세로 대비 비율이다."""

    color: str = Field("#000000", description="#RRGGBB")
    opacity: float = Field(0.5, ge=0, le=1)
    padding: float = Field(0.015, ge=0, le=0.1)
    radius: float = Field(0, ge=0, le=0.1)
