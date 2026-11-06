"""문구 배치 추천 요청 스키마.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field, field_validator

from app.core.layout_templates import FONT_STYLES, FontStyle, TemplateId
from app.schemas.layout_copy import LayoutCopy
from app.utils.image import decode_base64_image

MAX_PROPOSALS = 5


class LayoutRecommendRequest(BaseModel):
    """이미지 한 장과 역할별 문구로 위치·글꼴·스타일 추천안을 요청한다."""

    image_base64: str = Field(..., description="배치를 추천받을 이미지의 base64 문자열")
    copies: list[LayoutCopy] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="역할별 문구 1~3개 (역할 중복 불가)",
    )
    num_proposals: int = Field(
        MAX_PROPOSALS, ge=1, le=MAX_PROPOSALS, description="받을 추천안 수"
    )
    accent: str | None = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="문구 강조색 #RRGGBB. 문구 추천 결과(copies.accent)를 그대로 보낸다. "
        "없으면 강조색 없이 톤온톤으로 추천한다",
    )
    styles: list[FontStyle] = Field(
        default_factory=list,
        max_length=len(FONT_STYLES),
        description="글꼴 스타일 (어울리는 순서). 문구 추천 결과(copies.styles)를 그대로 "
        "보낸다. 추천안마다 앞에서부터 하나씩 쓰고, 모자라면 나머지 스타일로 채운다",
    )
    template_id: TemplateId | None = Field(
        None,
        description="레이아웃 지정. 보내면 이 템플릿으로만 추천안을 만든다 (제품을 가려도 "
        "쓴다). 스타일까지 지정하려면 styles 1개와 num_proposals 1을 함께 보낸다. "
        "없으면 이미지에 맞는 템플릿을 고른다",
    )

    @field_validator("image_base64")
    @classmethod
    def _check_image(cls, value: str) -> str:
        """이미지로 읽을 수 있는 base64인지 확인한다.

        Returns:
            str: 받은 값 그대로.

        Raises:
            ValueError: 이미지로 읽을 수 없을 때.
        """
        decode_base64_image(value)
        return value

    @field_validator("copies")
    @classmethod
    def _check_unique_roles(cls, value: list[LayoutCopy]) -> list[LayoutCopy]:
        """역할이 겹치지 않는지 확인한다.

        Returns:
            list[LayoutCopy]: 받은 값 그대로.

        Raises:
            ValueError: 같은 역할이 두 번 이상 있을 때.
        """
        roles = [copy.role for copy in value]
        if len(roles) != len(set(roles)):
            raise ValueError("같은 역할의 문구는 하나만 보낼 수 있습니다.")
        return value
