"""이미지 생성기 인터페이스.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-22
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
        seeds: list[int],
    ) -> list[str]:
        """프롬프트로 seed 개수만큼 이미지를 생성한다.

        Args:
            prompt: 영어 프롬프트.
            width: 이미지 너비.
            height: 이미지 높이.
            seeds: 이미지마다 사용할 seed 목록. 목록 길이만큼 이미지를 생성한다.

        Returns:
            list[str]: seeds 순서대로 생성한 PNG 이미지의 base64 문자열 목록.

        Raises:
            GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
        """
        ...
