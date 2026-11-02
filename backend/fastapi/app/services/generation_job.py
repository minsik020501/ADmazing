"""이미지 생성 작업(job)의 진행 상태.

생성일자: 2026-11-02
생성자: ven_choi
수정일자: 2026-11-02
수정자: ven_choi
"""

import threading
import time
from app.schemas.generate_response import GenerateResponse
from app.schemas.generation_job_status import GenerationJobStatus, JobStage
from app.services.generation_cancelled_error import GenerationCancelledError

_FINISHED_STAGES = ("done", "failed", "cancelled")


class GenerationJob:
    """작업 하나의 단계, step 진행률, 결과와 취소 요청을 보관한다.

    상태는 생성 스레드에서 바뀌고 SSE 응답(이벤트 루프)에서 읽으므로 잠금으로 보호한다.
    """

    def __init__(self, job_id: str) -> None:
        """번역 단계에서 시작하는 작업을 만든다.

        Args:
            job_id: 작업 id.
        """
        self.job_id = job_id
        self._lock = threading.Lock()
        self._cancel_requested = threading.Event()
        self._stage: JobStage = "translating"
        self._step: int | None = None
        self._total: int | None = None
        self._result: GenerateResponse | None = None
        self._error: str | None = None
        # 상태가 바뀔 때마다 1씩 늘려 SSE에서 바뀐 경우에만 보내게 한다
        self._version = 0
        self._finished_at: float | None = None

    @property
    def finished_at(self) -> float | None:
        """작업이 끝난 시각(time.monotonic). 진행 중이면 None."""
        return self._finished_at

    def snapshot(self) -> tuple[int, GenerationJobStatus]:
        """현재 상태를 한 번에 읽는다.

        Returns:
            tuple[int, GenerationJobStatus]: 상태 버전과 응답용 상태.
        """
        with self._lock:
            return self._version, GenerationJobStatus(
                job_id=self.job_id,
                stage=self._stage,
                step=self._step,
                total=self._total,
                result=self._result,
                error=self._error,
            )

    def cancel(self) -> None:
        """취소를 요청한다. 실제 중단은 생성 쪽에서 다음 확인 시점에 일어난다."""
        self._cancel_requested.set()

    def raise_if_cancelled(self) -> None:
        """취소가 요청되었으면 예외를 던진다.

        Raises:
            GenerationCancelledError: 취소가 요청되었을 때.
        """
        if self._cancel_requested.is_set():
            raise GenerationCancelledError

    def mark_queued(self) -> None:
        """번역을 마치고 앞선 생성이 끝나기를 기다리는 단계로 바꾼다."""
        self._update(stage="queued")

    def start_generating(self) -> None:
        """생성 차례가 되었을 때 호출한다.

        Raises:
            GenerationCancelledError: 기다리는 동안 취소가 요청되었을 때.
        """
        self.raise_if_cancelled()
        self._update(stage="generating")

    def report_step(self, step: int, total: int) -> None:
        """디노이징 step 진행률을 기록한다. 이미지 생성기의 step 콜백으로 쓴다.

        Args:
            step: 완료한 step 수.
            total: 전체 step 수.

        Raises:
            GenerationCancelledError: 취소가 요청되었을 때. 파이프라인을 바로 멈춘다.
        """
        self.raise_if_cancelled()
        self._update(step=step, total=total)

    def complete(self, result: GenerateResponse) -> None:
        """생성 결과를 저장하고 작업을 끝낸다.

        Args:
            result: 생성 결과.
        """
        self._update(stage="done", result=result)

    def fail(self, message: str) -> None:
        """에러 메시지를 저장하고 작업을 끝낸다.

        Args:
            message: 화면에 보여줄 에러 메시지.
        """
        self._update(stage="failed", error=message)

    def mark_cancelled(self) -> None:
        """취소된 상태로 작업을 끝낸다."""
        self._update(stage="cancelled")

    def _update(self, **fields) -> None:
        """상태 필드를 바꾸고 버전을 올린다. 끝난 작업이면 끝난 시각을 기록한다.

        Args:
            **fields: 바꿀 필드 (stage, step, total, result, error).
        """
        with self._lock:
            for name, value in fields.items():
                setattr(self, f"_{name}", value)
            self._version += 1
            if self._stage in _FINISHED_STAGES:
                self._finished_at = time.monotonic()
