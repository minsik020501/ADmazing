"""단독 문구 추천 요청 스키마.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from pydantic import BaseModel, Field, field_validator

from app.schemas.copy_requests import CopyRequests
from app.utils.image import decode_base64_image


class CopyRecommendRequest(BaseModel):
    """이미지 한 장의 문구를 다시 추천받을 때 쓰는 요청 본문."""

    image_base64: str = Field(..., description="문구를 추천받을 이미지의 base64 문자열")
    prompt: str = Field(..., min_length=1, description="한국어 광고 이미지 설명")
    copy_requests: CopyRequests | None = Field(
        None,
        description="역할별 문구 요청. AI가 참고해 문구를 쓰고, 요청에 든 가격·날짜·숫자는 "
        "바꾸지 않는다. 없거나 비운 역할은 AI가 자유롭게 추천한다",
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
