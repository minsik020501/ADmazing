"""광고 이미지 생성 흐름(번역 → 생성 → 이미지별 문구 추천 → 응답 조립) 서비스.

/api/generate와 /api/jobs가 같은 흐름을 쓰도록 라우터에서 분리했다.

생성일자: 2026-11-02
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from fastapi.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.image_ratio import IMAGE_RESOLUTIONS
from app.schemas.generate_request import GenerateRequest
from app.schemas.generate_response import GenerateResponse
from app.schemas.generated_image import GeneratedImage
from app.services.copy_recommend_service import recommend_copies_for_images
from app.services.copy_recommender import CopyRecommender
from app.services.generation_job import GenerationJob
from app.services.generation_runner import run_generation
from app.services.image_generator import ImageGenerator
from app.services.translator import translate_to_english
from app.utils.seed import make_seeds

GPU_OUT_OF_MEMORY_MESSAGE = (
    "GPU 메모리가 부족해 이미지를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요."
)


async def generate_ad_images(
    req: GenerateRequest,
    image_generator: ImageGenerator,
    copy_recommender: CopyRecommender,
    job: GenerationJob | None = None,
) -> GenerateResponse:
    """한국어 프롬프트를 영어로 번역한 뒤 광고 이미지를 NUM_IMAGES_PER_REQUEST장 생성하고,
    이미지마다 어울리는 문구를 추천한다.

    문구 추천에 실패한 이미지는 copies 대신 copies_error를 채우고, 작업은 실패시키지 않는다.

    Args:
        req: 한국어 프롬프트, 이미지 비율, 시드, 역할별 문구 요청을 담은 요청.
            해상도는 비율에 맞는 IMAGE_RESOLUTIONS 값을 사용한다.
        image_generator: 이미지 생성기.
        copy_recommender: 문구 추천기.
        job: 진행 상황을 기록하고 취소를 확인할 작업. 없으면 기록하지 않는다.

    Returns:
        GenerateResponse: 원본 프롬프트, 번역된 프롬프트, 비율과 해상도,
            이미지와 seed, 이미지별 추천 문구 목록.

    Raises:
        GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
        GenerationCancelledError: job이 취소되었을 때.
    """
    translated = await translate_to_english(req.prompt)
    if job is not None:
        # 번역은 중간에 멈출 수 없어 끝난 뒤에 취소를 확인한다
        job.raise_if_cancelled()
        job.mark_queued()

    seeds = make_seeds(req.seed, settings.num_images_per_request)
    width, height = IMAGE_RESOLUTIONS[req.ratio]
    images = await run_in_threadpool(
        run_generation,
        image_generator,
        translated,
        width,
        height,
        seeds,
        job,
    )
    # run_generation이 끝나면 GPU 잠금이 풀려 있으므로, 문구를 추천하는 동안
    # 다음 작업의 이미지 생성이 기다리지 않는다
    copies = await recommend_copies_for_images(
        copy_recommender,
        images,
        req.prompt,
        req.copy_requests.filled() if req.copy_requests else {},
        job,
    )

    return GenerateResponse(
        original_prompt=req.prompt,
        translated_prompt=translated,
        ratio=req.ratio,
        width=width,
        height=height,
        images=[
            GeneratedImage(
                image_base64=image, seed=seed, copies=image_copies, copies_error=error
            )
            for image, seed, (image_copies, error) in zip(images, seeds, copies)
        ],
    )
