"""이미지 생성기 인터페이스.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

from typing import Protocol


class ImageGenerator(Protocol):
    """프롬프트로 이미지를 생성하는 생성기의 공통 인터페이스."""

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int | None = None,
    ) -> str:
        """프롬프트로 이미지를 생성한다.

        Args:
            prompt: 영어 프롬프트.
            width: 이미지 너비.
            height: 이미지 높이.
            seed: 재현용 랜덤 시드. None이면 매번 다른 이미지를 생성한다.

        Returns:
            str: PNG 이미지의 base64 문자열.
        """
        ...
