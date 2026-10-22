"""에러 응답 스키마.

생성일자: 2026-10-22
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """HTTPException 에러 응답 본문 (OpenAPI 문서용)."""

    detail: str = Field(..., description="에러 메시지")
