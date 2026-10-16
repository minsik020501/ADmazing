"""모델 없이 더미 이미지를 반환하는 개발용 이미지 생성기.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

import textwrap

from PIL import Image, ImageDraw

from app.utils.image import to_base64


class MockImageGenerator:
    """프롬프트가 적힌 회색 더미 이미지를 반환한다 (torch 불필요)."""

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int | None = None,
    ) -> str:
        """프롬프트 텍스트가 적힌 더미 이미지를 생성한다.

        Args:
            prompt: 영어 프롬프트.
            width: 이미지 너비.
            height: 이미지 높이.
            seed: 사용하지 않음. 인터페이스 호환용.

        Returns:
            str: PNG 이미지의 base64 문자열.
        """
        image = Image.new("RGB", (width, height), "#e0e0e0")
        draw = ImageDraw.Draw(image)
        text = "[MOCK]\n" + "\n".join(textwrap.wrap(prompt, width=50))
        draw.multiline_text((16, 16), text, fill="#333333")
        return to_base64(image)
