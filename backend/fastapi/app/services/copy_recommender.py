"""문구 추천기 인터페이스.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Protocol

from app.core.copy_role import CopyRole
from app.services.copy_candidates import CopyCandidates


class CopyRecommender(Protocol):
    """이미지 한 장과 프롬프트로 역할별 광고 문구 후보와 강조색을 만드는 추천기."""

    async def recommend(
        self,
        image_base64: str,
        prompt: str,
        keywords: list[str],
        existing: dict[CopyRole, list[str]],
        counts: dict[CopyRole, int],
    ) -> CopyCandidates:
        """역할별로 문구 후보를 만들고, 문구에 쓸 강조색을 고른다.

        후보는 정리·중복 제거 전의 원본이다. 개수가 counts와 다를 수 있다.

        Args:
            image_base64: PNG 이미지의 base64 문자열.
            prompt: 사용자가 입력한 한국어 이미지 설명.
            keywords: 모든 문구에 글자 그대로 넣어야 하는 단어·문장.
            existing: 역할별로 앞서 받아 둔 AI 문구.
                톤과 정보를 맞추고 겹치지 않게 하는 데 쓴다.
            counts: 역할별로 필요한 AI 문구 수. 0인 역할은 만들지 않는다.

        Returns:
            CopyCandidates: 역할별 문구 후보와 강조색.

        Raises:
            CopyRecommendationError: 문구를 만들지 못했을 때.
        """
        ...
