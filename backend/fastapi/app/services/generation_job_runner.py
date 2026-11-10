"""이미지 생성 작업을 백그라운드에서 실행하는 서비스.

생성일자: 2026-11-02
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import asyncio
import logging

from app.schemas.generate_request import GenerateRequest
from app.services.ad_image_service import GPU_OUT_OF_MEMORY_MESSAGE, generate_ad_images
from app.services.copy_recommender import CopyRecommender
from app.services.generation_cancelled_error import GenerationCancelledError
from app.services.generation_job import GenerationJob
from app.services.gpu_out_of_memory_error import GpuOutOfMemoryError
from app.services.image_generator import ImageGenerator

logger = logging.getLogger(__name__)

# 실행 중인 작업 태스크가 가비지 컬렉션되지 않도록 끝날 때까지 참조를 들고 있는다
_running_tasks: set[asyncio.Task] = set()


def start_job(
    job: GenerationJob,
    req: GenerateRequest,
    image_generator: ImageGenerator,
    copy_recommender: CopyRecommender,
) -> None:
    """작업을 백그라운드 태스크로 실행한다. 응답을 기다리지 않고 바로 반환한다.

    Args:
        job: 진행 상황을 기록할 작업.
        req: 이미지 생성 요청.
        image_generator: 이미지 생성기.
        copy_recommender: 문구 추천기.
    """
    task = asyncio.create_task(_run_job(job, req, image_generator, copy_recommender))
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)


async def _run_job(
    job: GenerationJob,
    req: GenerateRequest,
    image_generator: ImageGenerator,
    copy_recommender: CopyRecommender,
) -> None:
    """이미지를 생성하고 문구를 추천한 뒤 결과, 에러, 취소 여부를 작업에 기록한다.

    Args:
        job: 진행 상황을 기록할 작업.
        req: 이미지 생성 요청.
        image_generator: 이미지 생성기.
        copy_recommender: 문구 추천기.
    """
    try:
        job.complete(
            await generate_ad_images(req, image_generator, copy_recommender, job)
        )
    except GenerationCancelledError:
        job.mark_cancelled()
    except GpuOutOfMemoryError:
        job.fail(GPU_OUT_OF_MEMORY_MESSAGE)
    except Exception:
        # 백그라운드 태스크라 예외가 응답으로 나가지 않으므로 로그로 남긴다
        logger.exception("이미지 생성 작업 실패: %s", job.job_id)
        job.fail("이미지 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
