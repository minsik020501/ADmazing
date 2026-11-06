"""OpenAI 없이 고정 문구를 돌려주는 개발용 문구 추천기.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import asyncio

from app.core.copy_role import CopyRole
from app.services.copy_candidates import CopyCandidates

# 진행률 화면을 확인할 수 있도록 흉내 내는 응답 시간
_MOCK_SECONDS = 0.5

_MOCK_ACCENT = "#E8743B"
_MOCK_STYLES = ["clean", "minimal_gothic"]
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
        "지금 구매하면 1+1 혜택",
        "전국 편의점에서 만나보세요",
        "한정 수량, 서둘러 주세요",
        "무료 배송으로 집 앞까지",
        "첫 구매 고객 10% 할인",
    ],
}


class MockCopyRecommender:
    """역할마다 고정 문구를 필요한 개수만큼, 강조색·스타일은 고정 값을 돌려준다."""

    async def recommend(
        self,
        image_base64: str,
        prompt: str,
        keywords: list[str],
        existing: dict[CopyRole, list[str]],
        counts: dict[CopyRole, int],
    ) -> CopyCandidates:
        """고정 문구 목록의 앞에서부터 필요한 개수만큼, 필수 단어를 앞에 붙여 돌려준다.

        Args:
            image_base64: 사용하지 않는다.
            prompt: 사용하지 않는다.
            keywords: 문구 앞에 붙일 필수 단어.
            existing: 사용하지 않는다.
            counts: 역할별로 필요한 문구 수.

        Returns:
            CopyCandidates: 역할별 고정 문구와 고정 강조색·스타일.
        """
        await asyncio.sleep(_MOCK_SECONDS)
        return CopyCandidates(
            copies={
                role: [
                    " ".join([*keywords, text]) for text in _MOCK_COPIES[role][:count]
                ]
                for role, count in counts.items()
            },
            accent=_MOCK_ACCENT,
            styles=list(_MOCK_STYLES),
        )
