"""광고 문구의 역할(title, subtitle, text)과 역할별 규칙.

문구 추천 결과의 역할 이름은 에디터 문구 상자의 role 값과 같다 (docs/text_layer_spec.md).

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Literal

CopyRole = Literal["title", "subtitle", "text"]

COPY_ROLES: tuple[CopyRole, ...] = ("title", "subtitle", "text")

# 역할마다 돌려줄 문구 수
COPIES_PER_ROLE = 5

# 요청이 없는 역할에서 AI가 추천하는 문구의 최대 글자 수. 넘는 문구는 버린다
AI_COPY_MAX_LENGTH: dict[CopyRole, int] = {"title": 15, "subtitle": 30, "text": 60}

# 역할별 문구 요청(copy_requests)의 최대 글자 수.
# 요청이 있는 역할은 요청 내용을 담을 수 있게 추천 문구도 이 글자 수까지 허용한다
COPY_REQUEST_MAX_LENGTH: dict[CopyRole, int] = {
    "title": 20,
    "subtitle": 30,
    "text": 100,
}

# 사용자가 직접 넣는 문장의 최대 글자 수 (문구 상자 text 상한과 같다)
USER_COPY_MAX_LENGTH = 200


def copy_max_length(role: CopyRole, requests: dict[CopyRole, str]) -> int:
    """요청 유무에 따른 역할별 추천 문구 최대 글자 수.

    Args:
        role: 역할.
        requests: 역할별 문구 요청 (요청이 없는 역할은 키가 없다).

    Returns:
        int: 요청이 있으면 COPY_REQUEST_MAX_LENGTH와 AI_COPY_MAX_LENGTH 중 큰 값,
            없으면 AI_COPY_MAX_LENGTH.
    """
    if role in requests:
        return max(AI_COPY_MAX_LENGTH[role], COPY_REQUEST_MAX_LENGTH[role])
    return AI_COPY_MAX_LENGTH[role]
