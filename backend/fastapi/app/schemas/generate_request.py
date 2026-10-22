"""이미지 생성 요청 스키마.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from pydantic import BaseModel, Field

from app.core.config import settings
from app.utils.seed import MAX_SEED

# 이미지마다 seed를 1씩 늘려 쓰므로 마지막 이미지의 seed도 MAX_SEED를 넘지 않게 한다
MAX_REQUEST_SEED = MAX_SEED - (settings.num_images_per_request - 1)


class GenerateRequest(BaseModel):
    """이미지 생성 API 요청 본문."""

    prompt: str = Field(..., min_length=1, description="한국어 광고 이미지 설명")
    seed: int | None = Field(
        None,
        ge=0,
        le=MAX_REQUEST_SEED,
        description=(
            "재현용 seed. 이미지마다 seed, seed+1, ... 순서로 사용. 없으면 랜덤. "
            "상한은 2^32-1 - (NUM_IMAGES_PER_REQUEST-1)"
        ),
    )
    width: int | None = Field(
        None,
        ge=256,
        le=1536,
        multiple_of=8,
        description="이미지 너비 (8의 배수). 없으면 DEFAULT_IMAGE_WIDTH 사용",
    )
    height: int | None = Field(
        None,
        ge=256,
        le=1536,
        multiple_of=8,
        description="이미지 높이 (8의 배수). 없으면 DEFAULT_IMAGE_HEIGHT 사용",
    )
