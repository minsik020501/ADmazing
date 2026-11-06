"""이미지 생성 작업 상태 스키마.

생성일자: 2026-11-02
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.generate_response import GenerateResponse

JobStage = Literal[
    "translating",
    "queued",
    "generating",
    "recommending_copy",
    "done",
    "failed",
    "cancelled",
]


class GenerationJobStatus(BaseModel):
    """작업 상태 조회 응답과 SSE 이벤트 본문."""

    job_id: str
    stage: JobStage = Field(
        ...,
        description=(
            "translating: 번역 중, queued: 앞선 생성 대기 중, generating: 생성 중, "
            "recommending_copy: 이미지별 문구 추천 중, "
            "done: 완료, failed: 실패, cancelled: 취소됨"
        ),
    )
    step: int | None = Field(
        None, description="완료한 디노이징 step 수. step == total이면 이미지 디코딩 중"
    )
    total: int | None = Field(None, description="전체 디노이징 step 수")
    copy_done: int | None = Field(
        None,
        description=(
            "문구 추천이 끝난 이미지 수 (성공·실패 모두). "
            "recommending_copy 전에는 null"
        ),
    )
    copy_total: int | None = Field(
        None,
        description="문구를 추천할 이미지 수. recommending_copy 전에는 null",
    )
    result: GenerateResponse | None = Field(None, description="stage가 done일 때 결과")
    error: str | None = Field(None, description="stage가 failed일 때 에러 메시지")
