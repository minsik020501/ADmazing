"""광고 이미지 생성 라우터.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-11-02
수정자: ven_choi
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_image_generator
from app.schemas.error_response import ErrorResponse
from app.schemas.generate_request import GenerateRequest
from app.schemas.generate_response import GenerateResponse
from app.services.ad_image_service import GPU_OUT_OF_MEMORY_MESSAGE, generate_ad_images
from app.services.gpu_out_of_memory_error import GpuOutOfMemoryError
from app.services.image_generator import ImageGenerator

router = APIRouter(tags=["generate"])


@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "이미지 생성 중 GPU 메모리 부족",
        },
    },
)
async def generate(
    req: GenerateRequest,
    image_generator: ImageGenerator = Depends(get_image_generator),
):
    """한국어 프롬프트를 영어로 번역한 뒤 광고 이미지를 NUM_IMAGES_PER_REQUEST장 생성한다.

    생성이 끝날 때까지 응답을 기다린다. 진행률과 취소가 필요하면 /api/jobs를 쓴다.

    Args:
        req: 한국어 프롬프트, 이미지 비율, 시드를 담은 요청.
            해상도는 비율에 맞는 IMAGE_RESOLUTIONS 값을 사용한다.
        image_generator: 의존성으로 주입되는 이미지 생성기.

    Returns:
        GenerateResponse: 원본 프롬프트, 번역된 프롬프트, 비율과 해상도,
            이미지와 seed 목록.

    Raises:
        HTTPException: 생성 중 GPU 메모리가 부족할 때 (503).
    """
    try:
        return await generate_ad_images(req, image_generator)
    except GpuOutOfMemoryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=GPU_OUT_OF_MEMORY_MESSAGE,
        )
