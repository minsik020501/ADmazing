"""광고 이미지 생성 라우터.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.api.deps import get_image_generator
from app.core.config import settings
from app.schemas.generate_request import GenerateRequest
from app.schemas.generate_response import GenerateResponse
from app.services.image_generator import ImageGenerator
from app.services.translator import translate_to_english

router = APIRouter(tags=["generate"])


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    req: GenerateRequest,
    image_generator: ImageGenerator = Depends(get_image_generator),
):
    """한국어 프롬프트를 영어로 번역한 뒤 광고 이미지를 생성한다.

    Args:
        req: 한국어 프롬프트, 이미지 크기, 시드를 담은 요청.
            크기가 없으면 DEFAULT_IMAGE_WIDTH/HEIGHT를 사용한다.
        image_generator: 의존성으로 주입되는 이미지 생성기.

    Returns:
        GenerateResponse: 원본 프롬프트, 번역된 프롬프트, PNG base64 이미지.
    """
    translated = await translate_to_english(req.prompt)
    image_base64 = await run_in_threadpool(
        image_generator.generate,
        translated,
        req.width or settings.default_image_width,
        req.height or settings.default_image_height,
        req.seed,
    )

    return GenerateResponse(
        original_prompt=req.prompt,
        translated_prompt=translated,
        image_base64=image_base64,
    )
