"""배치를 추천받을 문구 하나의 스키마.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.core.copy_role import CopyRole, USER_COPY_MAX_LENGTH


class LayoutCopy(BaseModel):
    """역할과 문구. 문구는 모델이 고치지 않고 그대로 문구 상자에 들어간다."""

    role: CopyRole = Field(..., description="title, subtitle, text")
    text: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=USER_COPY_MAX_LENGTH
        ),
    ] = Field(..., description="문구. 줄바꿈은 \\n")
