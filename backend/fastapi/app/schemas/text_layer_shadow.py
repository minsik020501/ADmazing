"""문구 상자 그림자 스키마 (docs/text_layer_spec.md의 shadow).

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field


class TextLayerShadow(BaseModel):
    """글자 그림자. 흐림과 거리는 이미지 세로 대비 비율이다."""

    color: str = Field("#000000", description="#RRGGBB")
    blur: float = Field(0.01, ge=0, le=0.1)
    offsetX: float = Field(0.003, ge=-0.1, le=0.1, description="오른쪽이 +")
    offsetY: float = Field(0.003, ge=-0.1, le=0.1, description="아래가 +")
    opacity: float = Field(0.5, ge=0, le=1)
