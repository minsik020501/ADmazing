"""문구 상자 외곽선 스키마 (docs/text_layer_spec.md의 stroke).

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Literal

from pydantic import BaseModel, Field


class TextLayerStroke(BaseModel):
    """글자 외곽선."""

    color: str = Field("#000000", description="#RRGGBB")
    width: float = Field(0.004, ge=0, le=0.05, description="두께 (이미지 세로 대비)")
    opacity: float = Field(1, ge=0, le=1)
    join: Literal["round", "miter"] = Field("round", description="모서리 모양")
