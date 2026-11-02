"""진행률 조회와 취소를 지원하는 이미지 생성 작업 라우터.

생성일자: 2026-11-02
생성자: ven_choi
수정일자: 2026-11-02
수정자: ven_choi
"""

import asyncio
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_image_generator, get_job_store
from app.schemas.error_response import ErrorResponse
from app.schemas.generate_request import GenerateRequest
from app.schemas.generation_job_created import GenerationJobCreated
from app.schemas.generation_job_status import GenerationJobStatus
from app.services.generation_job import GenerationJob
from app.services.generation_job_runner import start_job
from app.services.generation_job_store import GenerationJobStore
from app.services.image_generator import ImageGenerator

router = APIRouter(tags=["jobs"])

# SSE에서 작업 상태가 바뀌었는지 확인하는 간격
_EVENT_POLL_SECONDS = 0.2
# 대기가 길어져도 프록시가 연결을 끊지 않도록 주석 줄을 보내는 간격
_KEEP_ALIVE_SECONDS = 15
_FINISHED_STAGES = ("done", "failed", "cancelled")
_NOT_FOUND_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "작업이 없거나 끝난 지 오래되어 지워짐",
    },
}


def _get_job_or_404(job_id: str, job_store: GenerationJobStore) -> GenerationJob:
    """작업 id로 작업을 찾는다.

    Args:
        job_id: 작업 id.
        job_store: 작업 저장소.

    Returns:
        GenerationJob: 찾은 작업.

    Raises:
        HTTPException: 작업이 없을 때 (404).
    """
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이미지 생성 작업을 찾을 수 없습니다.",
        )
    return job


@router.post(
    "/jobs",
    response_model=GenerationJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_job(
    req: GenerateRequest,
    image_generator: ImageGenerator = Depends(get_image_generator),
    job_store: GenerationJobStore = Depends(get_job_store),
):
    """이미지 생성 작업을 등록하고 바로 작업 id를 반환한다.

    진행 상황은 GET /jobs/{job_id}/events(SSE)로 받고, DELETE /jobs/{job_id}로 취소한다.

    Args:
        req: 한국어 프롬프트, 이미지 비율, 시드를 담은 요청.
        image_generator: 의존성으로 주입되는 이미지 생성기.
        job_store: 의존성으로 주입되는 작업 저장소.

    Returns:
        GenerationJobCreated: 등록된 작업 id.
    """
    job = job_store.create()
    start_job(job, req, image_generator)
    return GenerationJobCreated(job_id=job.job_id)


@router.get(
    "/jobs/{job_id}",
    response_model=GenerationJobStatus,
    responses=_NOT_FOUND_RESPONSE,
)
async def get_job(
    job_id: str,
    job_store: GenerationJobStore = Depends(get_job_store),
):
    """작업의 현재 상태를 한 번 조회한다.

    Args:
        job_id: 작업 id.
        job_store: 의존성으로 주입되는 작업 저장소.

    Returns:
        GenerationJobStatus: 작업 단계, step 진행률, 결과 또는 에러.

    Raises:
        HTTPException: 작업이 없을 때 (404).
    """
    _, job_status = _get_job_or_404(job_id, job_store).snapshot()
    return job_status


@router.get(
    "/jobs/{job_id}/events",
    response_class=StreamingResponse,
    responses={
        status.HTTP_200_OK: {
            "content": {"text/event-stream": {}},
            "description": "상태가 바뀔 때마다 GenerationJobStatus JSON을 data로 보낸다. "
            "작업이 끝나면(done, failed, cancelled) 스트림을 닫는다.",
        },
        **_NOT_FOUND_RESPONSE,
    },
)
async def stream_job_events(
    job_id: str,
    request: Request,
    job_store: GenerationJobStore = Depends(get_job_store),
):
    """작업 상태를 Server-Sent Events로 보낸다.

    Args:
        job_id: 작업 id.
        request: 연결이 끊겼는지 확인할 요청 객체.
        job_store: 의존성으로 주입되는 작업 저장소.

    Returns:
        StreamingResponse: text/event-stream 응답.

    Raises:
        HTTPException: 작업이 없을 때 (404).
    """
    job = _get_job_or_404(job_id, job_store)
    return StreamingResponse(
        _job_events(job, request),
        media_type="text/event-stream",
        # 프록시(nginx 등)가 이벤트를 모아서 보내지 않도록 버퍼링을 끈다
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _job_events(job: GenerationJob, request: Request) -> AsyncIterator[str]:
    """작업 상태가 바뀔 때마다 SSE 이벤트 문자열을 만든다.

    Args:
        job: 상태를 보낼 작업.
        request: 연결이 끊겼는지 확인할 요청 객체.

    Yields:
        str: SSE 이벤트 문자열 (data 줄 또는 keep-alive 주석 줄).
    """
    last_version = -1
    last_sent = time.monotonic()
    while not await request.is_disconnected():
        version, job_status = job.snapshot()
        if version != last_version:
            last_version = version
            last_sent = time.monotonic()
            yield f"data: {job_status.model_dump_json()}\n\n"
            if job_status.stage in _FINISHED_STAGES:
                return
        elif time.monotonic() - last_sent > _KEEP_ALIVE_SECONDS:
            last_sent = time.monotonic()
            yield ": keep-alive\n\n"
        await asyncio.sleep(_EVENT_POLL_SECONDS)


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND_RESPONSE,
)
async def cancel_job(
    job_id: str,
    job_store: GenerationJobStore = Depends(get_job_store),
):
    """작업 취소를 요청한다. 이미 끝난 작업이면 아무 일도 하지 않는다.

    생성 중이면 다음 step이 끝날 때 멈추고, 이미지 디코딩 중이면 디코딩이 끝난 뒤 취소된다.

    Args:
        job_id: 작업 id.
        job_store: 의존성으로 주입되는 작업 저장소.

    Returns:
        Response: 본문 없는 204 응답.

    Raises:
        HTTPException: 작업이 없을 때 (404).
    """
    _get_job_or_404(job_id, job_store).cancel()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
