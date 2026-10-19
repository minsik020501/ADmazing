"""헬스 체크 라우터.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-19
수정자: ven_choi
"""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health_response import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health():
    """서버 상태와 현재 이미지 생성 설정을 조회한다.

    Returns:
        HealthResponse: 서버 상태, 이미지 생성 모드, 모델 경로, LoRA 경로.
    """
    return HealthResponse(
        status="ok",
        image_generator=settings.image_generator,
        model_path=settings.model_path,
        lora_path=settings.lora_path,
    )
