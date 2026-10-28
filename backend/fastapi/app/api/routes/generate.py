"""광고 이미지 생성 라우터.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.api.deps import get_image_generator
from app.core.config import settings
from app.core.image_ratio import IMAGE_RESOLUTIONS
from app.schemas.error_response import ErrorResponse
from app.schemas.generate_request import GenerateRequest
from app.schemas.generate_response import GenerateResponse
from app.schemas.generated_image import GeneratedImage
from app.services.generation_runner import run_generation
from app.services.gpu_out_of_memory_error import GpuOutOfMemoryError
from app.services.image_generator import ImageGenerator
from app.services.translator import translate_to_english
from app.utils.seed import make_seeds

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
    translated = await translate_to_english(req.prompt)
    seeds = make_seeds(req.seed, settings.num_images_per_request)
    width, height = IMAGE_RESOLUTIONS[req.ratio]
    try:
        images = await run_in_threadpool(
            run_generation,
            image_generator,
            translated,
            width,
            height,
            seeds,
        )
    except GpuOutOfMemoryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GPU 메모리가 부족해 이미지를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        )

    return GenerateResponse(
        original_prompt=req.prompt,
        translated_prompt=translated,
        ratio=req.ratio,
        width=width,
        height=height,
        images=[
            GeneratedImage(image_base64=image, seed=seed)
            for image, seed in zip(images, seeds)
        ],
    )
