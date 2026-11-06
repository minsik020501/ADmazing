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

# 역할마다 돌려줄 문구 수 (사용자 문장 포함)
COPIES_PER_ROLE = 5

# AI가 추천하는 문구의 역할별 최대 글자 수. 넘는 문구는 버린다
AI_COPY_MAX_LENGTH: dict[CopyRole, int] = {"title": 15, "subtitle": 30, "text": 60}

# 사용자가 직접 넣는 문장의 최대 글자 수 (문구 상자 text 상한과 같다)
USER_COPY_MAX_LENGTH = 200
