"""문구 배치 추천 모델 인터페이스.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from typing import Protocol

from PIL import Image

from app.schemas.layout_copy import LayoutCopy


class LayoutRecommender(Protocol):
    """이미지와 지시문을 받아 압축 추천안 JSON 문자열을 생성하는 모델."""

    def generate(
        self,
        image: Image.Image,
        copies: list[LayoutCopy],
        user_prompt: str,
        sample: bool = False,
    ) -> str:
        """모델 출력 문자열을 생성한다. GPU 잠금을 잡은 상태에서 호출한다.

        Args:
            image: 배치를 추천받을 이미지 (원본 크기).
            copies: 배치할 역할별 문구.
            user_prompt: layout_prompt.build_user_prompt로 만든 지시문.
            sample: True면 샘플링으로 생성한다 (재시도용). False면 greedy.

        Returns:
            str: 모델 출력 문자열 (압축 추천안 JSON).

        Raises:
            GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
        """
        ...

    def detect_subjects(self, image: Image.Image) -> str:
        """가리면 안 되는 영역(제품, 사람 얼굴)을 찾는 출력 문자열을 생성한다.

        GPU 잠금을 잡은 상태에서 호출한다. 지시문은 layout_prompt.SUBJECT_PROMPT다.

        Args:
            image: 배치를 추천받을 이미지 (원본 크기).

        Returns:
            str: [{"label", "bbox_2d"}] 형태의 JSON 문자열 (0~1000 좌표).

        Raises:
            GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
        """
        ...
