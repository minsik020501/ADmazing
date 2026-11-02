"""이미지 생성 작업 등록 응답 스키마.

생성일자: 2026-11-02
생성자: ven_choi
수정일자: 2026-11-02
수정자: ven_choi
"""

from pydantic import BaseModel, Field


class GenerationJobCreated(BaseModel):
    """작업 등록 API 응답 본문."""

    job_id: str = Field(..., description="진행 상황 조회와 취소에 쓰는 작업 id")
