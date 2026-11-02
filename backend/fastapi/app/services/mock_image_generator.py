"""모델 없이 더미 이미지를 반환하는 개발용 이미지 생성기.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-11-02
수정자: ven_choi
"""

import textwrap
import time

from PIL import Image, ImageDraw

from app.services.image_generator import StepCallback
from app.utils.image import to_base64

# 진행률 화면을 GPU 없이 확인할 수 있도록 흉내 내는 step 수와 step당 시간
_MOCK_STEPS = 8
_MOCK_STEP_SECONDS = 0.4


class MockImageGenerator:
    """프롬프트가 적힌 회색 더미 이미지를 반환한다 (torch 불필요)."""

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seeds: list[int],
        on_step: StepCallback | None = None,
    ) -> list[str]:
        """프롬프트 텍스트가 적힌 더미 이미지를 seed 개수만큼 생성한다.

        Args:
            prompt: 영어 프롬프트.
            width: 이미지 너비.
            height: 이미지 높이.
            seeds: 이미지마다 사용할 seed 목록. 이미지에 번호와 함께 적기만 한다.
            on_step: 있으면 step을 흉내 내며 step마다 호출한다. 없으면 바로 반환한다.

        Returns:
            list[str]: PNG 이미지의 base64 문자열 목록.

        Raises:
            GenerationCancelledError: on_step에서 취소되었을 때.
        """
        if on_step is not None:
            for step in range(1, _MOCK_STEPS + 1):
                time.sleep(_MOCK_STEP_SECONDS)
                on_step(step, _MOCK_STEPS)

        wrapped = "\n".join(textwrap.wrap(prompt, width=50))
        images = []
        for index, seed in enumerate(seeds, start=1):
            image = Image.new("RGB", (width, height), "#e0e0e0")
            draw = ImageDraw.Draw(image)
            text = f"[MOCK {index}/{len(seeds)}] seed={seed}\n{wrapped}"
            draw.multiline_text((16, 16), text, fill="#333333")
            images.append(to_base64(image))
        return images
