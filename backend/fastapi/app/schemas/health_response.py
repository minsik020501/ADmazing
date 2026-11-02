"""헬스 체크 응답 스키마.

생성일자: 2026-10-19
생성자: ven_choi
수정일자: 2026-10-28
수정자: ven_choi
"""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """헬스 체크 API 응답 본문."""

    status: Literal["ok"] = Field(..., description="서버 상태")
    image_generator: Literal["mock", "diffusers", "sdxl", "zimage"] = Field(
        ..., description="이미지 생성 모드"
    )
    model_path: str = Field(..., description="Hugging Face 모델 이름 또는 산출물 경로")
    lora_path: str | None = Field(None, description="LoRA 산출물 경로 (없으면 null)")
    num_images_per_request: int = Field(..., description="요청당 생성 이미지 장수")
