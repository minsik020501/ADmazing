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
    """이미지 한 장과 프롬프트로 문구 묶음 후보와 강조색·글꼴 스타일을 만드는 추천기."""

    async def recommend(
        self,
        image_base64: str,
        prompt: str,
        requests: dict[CopyRole, str],
        existing: list[dict[CopyRole, str]],
        count: int,
    ) -> CopyCandidates:
        """title, subtitle, text를 한 묶음으로 문구 묶음 후보를 만들고, 강조색을 고른다.

        후보는 정리·중복 제거 전의 원본이다. 개수가 count와 다를 수 있다.

        Args:
            image_base64: PNG 이미지의 base64 문자열.
            prompt: 사용자가 입력한 한국어 이미지 설명.
            requests: 역할별 문구 요청. AI가 참고해 쓰고, 요청의 숫자는 바꾸지 않는다.
                요청이 없는 역할은 키가 없다.
            existing: 앞서 받아 둔 문구 묶음. 톤을 맞추고 겹치지 않게 하는 데 쓴다.
            count: 필요한 문구 묶음 수.

        Returns:
            CopyCandidates: 문구 묶음 후보와 강조색·글꼴 스타일.

        Raises:
            CopyRecommendationError: 문구를 만들지 못했을 때.
        """
        ...
