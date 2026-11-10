"""OpenAI 없이 고정 문구를 돌려주는 개발용 문구 추천기.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import asyncio

from app.core.copy_role import CopyRole, copy_max_length
from app.services.copy_candidates import CopyCandidates

# 진행률 화면을 확인할 수 있도록 흉내 내는 응답 시간
_MOCK_SECONDS = 0.5

_MOCK_ACCENT = "#E8743B"
_MOCK_STYLES = ["clean", "minimal_gothic"]
# 요청 문구가 묶음마다 같으면 중복으로 버려지므로 묶음마다 다른 기호를 붙인다.
# 숫자를 붙이면 요청에 없는 숫자가 생겨 버려진다
_MOCK_SUFFIXES = ["", " ✦", " ★", " ♥", " ♪"]
# 같은 번호끼리 한 묶음이다
_MOCK_COPIES: dict[CopyRole, list[str]] = {
    "title": [
        "여름을 마시다",
        "지금, 시원하게",
        "한 모금의 휴식",
        "톡 쏘는 순간",
        "오늘의 기분",
    ],
    "subtitle": [
        "바다를 닮은 청량함",
        "하루의 끝에 만나는 상쾌함",
        "가볍게 즐기는 특별한 맛",
        "당신을 위한 작은 선물",
        "매일 새로운 기분 전환",
    ],
    "text": [
        "지금 가까운 매장에서 만나보세요",
        "전국 편의점에서 만나보세요",
        "한정 수량, 서둘러 주세요",
        "무료 배송으로 집 앞까지",
        "첫 구매 고객에게 드리는 혜택",
    ],
}


class MockCopyRecommender:
    """고정 문구 묶음을 필요한 개수만큼, 강조색·스타일은 고정 값을 돌려준다."""

    async def recommend(
        self,
        image_base64: str,
        prompt: str,
        requests: dict[CopyRole, str],
        existing: list[dict[CopyRole, str]],
        count: int,
    ) -> CopyCandidates:
        """앞서 받은 묶음 다음부터 필요한 개수만큼 고정 문구 묶음을 돌려준다.

        요청이 있는 역할은 고정 문구 대신 요청 내용을 그대로 쓴다.

        Args:
            image_base64: 사용하지 않는다.
            prompt: 사용하지 않는다.
            requests: 역할별 문구 요청.
            existing: 앞서 받은 묶음 (개수만 쓴다).
            count: 필요한 묶음 수.

        Returns:
            CopyCandidates: 고정 문구 묶음과 고정 강조색·스타일.
        """
        await asyncio.sleep(_MOCK_SECONDS)
        start = len(existing)
        indices = range(start, min(start + count, len(_MOCK_COPIES["title"])))
        return CopyCandidates(
            sets=[
                {
                    role: (
                        _requested_copy(role, requests[role], index)
                        if role in requests
                        else texts[index]
                    )
                    for role, texts in _MOCK_COPIES.items()
                }
                for index in indices
            ],
            accent=_MOCK_ACCENT,
            styles=list(_MOCK_STYLES),
        )


def _requested_copy(role: CopyRole, request: str, index: int) -> str:
    """요청 문구 뒤에 묶음 번호에 맞는 기호를 붙인다. 최대 글자 수를 넘으면 요청을 자른다.

    Returns:
        str: 요청이 있는 역할의 고정 문구.
    """
    suffix = _MOCK_SUFFIXES[index % len(_MOCK_SUFFIXES)]
    limit = copy_max_length(role, {role: request}) - len(suffix)
    return request[:limit].rstrip() + suffix
