"""문구 추천의 필수 단어·문장 타입.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Annotated

from pydantic import Field, StringConstraints

from app.core.copy_role import KEYWORD_MAX_LENGTH, MAX_KEYWORDS

# 필수 단어·문장 하나 (앞뒤 공백은 지운다)
CopyKeyword = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=KEYWORD_MAX_LENGTH
    ),
]


def keywords_field():
    """요청 본문에 쓰는 필수 단어·문장 목록 필드를 만든다.

    Returns:
        FieldInfo: pydantic 필드 정의.
    """
    return Field(
        default_factory=list,
        max_length=MAX_KEYWORDS,
        description=(
            f"추천 문구에 꼭 들어가야 하는 단어·문장 (0~{MAX_KEYWORDS}개, 각 "
            f"{KEYWORD_MAX_LENGTH}자 이하). 역할과 상관없이 모든 추천 문구에 글자 그대로 "
            "들어간다. 없으면 자유롭게 추천한다"
        ),
    )
