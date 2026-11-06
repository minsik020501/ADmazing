"""사용자가 직접 넣은 역할별 문장 스키마.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.core.copy_role import COPIES_PER_ROLE, USER_COPY_MAX_LENGTH, CopyRole

UserCopyText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=USER_COPY_MAX_LENGTH
    ),
]


class UserCopies(BaseModel):
    """역할별로 사용자가 직접 넣은 문장. 추천 결과의 앞쪽에 그대로 들어간다."""

    title: list[UserCopyText] = Field(
        default_factory=list,
        max_length=COPIES_PER_ROLE,
        description=f"타이틀 문장 (0~{COPIES_PER_ROLE}개)",
    )
    subtitle: list[UserCopyText] = Field(
        default_factory=list,
        max_length=COPIES_PER_ROLE,
        description=f"서브타이틀 문장 (0~{COPIES_PER_ROLE}개)",
    )
    text: list[UserCopyText] = Field(
        default_factory=list,
        max_length=COPIES_PER_ROLE,
        description=f"본문 문장 (0~{COPIES_PER_ROLE}개)",
    )

    def of(self, role: CopyRole) -> list[str]:
        """역할의 사용자 문장 목록을 반환한다.

        Returns:
            list[str]: 사용자가 넣은 순서대로의 문장 목록.
        """
        return getattr(self, role)
