"""이미지 변환 유틸리티.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

import base64
import io

from PIL import Image


def to_base64(image: Image.Image) -> str:
    """PIL 이미지를 PNG base64 문자열로 변환한다.

    Returns:
        str: PNG 이미지의 base64 문자열.
    """
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
