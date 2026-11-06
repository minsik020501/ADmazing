"""단독 문구 추천 요청 스키마.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field, field_validator

from app.schemas.user_copies import UserCopies
from app.utils.image import decode_base64_image


class CopyRecommendRequest(BaseModel):
    """이미지 한 장의 문구를 다시 추천받을 때 쓰는 요청 본문."""

    image_base64: str = Field(..., description="문구를 추천받을 이미지의 base64 문자열")
    prompt: str = Field(..., min_length=1, description="한국어 광고 이미지 설명")
    user_copies: UserCopies = Field(
        default_factory=UserCopies,
        description="역할별로 사용자가 직접 넣은 문장. 앞에 두고 남는 자리를 AI 문구로 채운다",
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
