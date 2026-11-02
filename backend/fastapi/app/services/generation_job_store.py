"""이미지 생성 작업을 메모리에 보관하는 저장소.

생성일자: 2026-11-02
생성자: ven_choi
수정일자: 2026-11-02
수정자: ven_choi
"""

import time
import uuid

from app.services.generation_job import GenerationJob

# 결과에 base64 이미지가 들어 있어 끝난 작업은 이 시간이 지나면 지운다
_FINISHED_JOB_TTL_SECONDS = 600


class GenerationJobStore:
    """작업 id로 작업을 찾는 메모리 저장소.

    서버가 프로세스 하나로 동작하므로 별도 저장소 없이 메모리에 둔다.
    이벤트 루프에서만 접근하므로 잠금이 필요 없다.
    """

    def __init__(self) -> None:
        """빈 저장소를 만든다."""
        self._jobs: dict[str, GenerationJob] = {}

    def create(self) -> GenerationJob:
        """새 작업을 만들어 저장한다. 오래전에 끝난 작업은 이때 함께 지운다.

        Returns:
            GenerationJob: 새로 만든 작업.
        """
        self._remove_expired()
        job = GenerationJob(uuid.uuid4().hex)
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> GenerationJob | None:
        """작업 id로 작업을 찾는다.

        Args:
            job_id: 작업 id.

        Returns:
            GenerationJob | None: 찾은 작업. 없거나 이미 지워졌으면 None.
        """
        return self._jobs.get(job_id)

    def _remove_expired(self) -> None:
        """끝난 지 _FINISHED_JOB_TTL_SECONDS가 지난 작업을 지운다."""
        now = time.monotonic()
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.finished_at is not None
            and now - job.finished_at > _FINISHED_JOB_TTL_SECONDS
        ]
        for job_id in expired:
            del self._jobs[job_id]
