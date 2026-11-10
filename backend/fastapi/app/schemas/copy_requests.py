"""역할별 문구 요청 스키마.

문구 요청은 문구에 그대로 넣는 값이 아니라 AI가 참고해 역할에 맞게 다시 쓰는 내용이다.
요청에 든 가격·날짜·숫자는 바꾸지 않는다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.core.copy_role import COPY_REQUEST_MAX_LENGTH, COPY_ROLES, CopyRole


def _request_field(role: CopyRole, description: str):
    """역할 하나의 문구 요청 필드를 만든다.

    Returns:
        FieldInfo: pydantic 필드 정의.
    """
    return Field(
        None,
        description=f"{description} ({COPY_REQUEST_MAX_LENGTH[role]}자 이하). "
        "AI가 참고해 문구를 쓴다. 비우면 AI가 자유롭게 추천한다",
    )


def _request_type(role: CopyRole):
    """역할 하나의 문구 요청 타입 (앞뒤 공백은 지운다).

    Returns:
        type: 글자 수 제한이 붙은 str 타입.
    """
    return Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, max_length=COPY_REQUEST_MAX_LENGTH[role]
        ),
    ]


class CopyRequests(BaseModel):
    """title, subtitle, text 역할마다 AI에게 부탁할 문구 내용."""

    title: _request_type("title") | None = _request_field(
        "title", "타이틀 요청. 예: 김포 강아지 카페 첫 방문 할인"
    )
    subtitle: _request_type("subtitle") | None = _request_field(
        "subtitle", "서브타이틀 요청. 예: 넓은 공간에서 귀여운 강아지들과 함께 놀아요"
    )
    text: _request_type("text") | None = _request_field(
        "text", "본문 요청. 예: 2027년 1월까지 첫 방문 시 입장료 30% 할인"
    )

    def filled(self) -> dict[CopyRole, str]:
        """내용이 있는 역할의 요청만 모은다.

        Returns:
            dict[CopyRole, str]: 역할별 요청. 비었거나 공백뿐인 역할은 뺀다.
        """
        return {role: value for role in COPY_ROLES if (value := getattr(self, role))}
