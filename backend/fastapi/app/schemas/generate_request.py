"""이미지 생성 요청 스키마.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.utils.seed import MAX_SEED


class GenerateRequest(BaseModel):
    """이미지 생성 API 요청 본문."""

    prompt: str = Field(..., min_length=1, description="한국어 광고 이미지 설명")
    seed: int | None = Field(
        None,
        ge=0,
        description="재현용 seed. 이미지마다 seed, seed+1, ... 순서로 사용. 없으면 랜덤",
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

    @field_validator("seed")
    @classmethod
    def check_seed_range(cls, seed: int | None) -> int | None:
        """이미지마다 1씩 늘린 seed가 MAX_SEED를 넘지 않는지 검사한다.

        Args:
            seed: 요청 seed.

        Returns:
            int | None: 검사를 통과한 seed.

        Raises:
            ValueError: 마지막 이미지의 seed가 MAX_SEED를 넘을 때.
        """
        max_request_seed = MAX_SEED - (settings.num_images_per_request - 1)
        if seed is not None and seed > max_request_seed:
            raise ValueError(f"seed는 {max_request_seed} 이하여야 합니다.")
        return seed
