"""이미지 변환 유틸리티.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-11-06
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


def decode_base64_image(image_base64: str) -> Image.Image:
    """base64 문자열을 PIL 이미지로 읽는다.

    Returns:
        Image.Image: 읽은 이미지.

    Raises:
        ValueError: base64 형식이 틀렸거나 이미지로 읽을 수 없을 때.
    """
    try:
        data = base64.b64decode(image_base64, validate=True)
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as error:
        raise ValueError("이미지를 읽을 수 없습니다.") from error
    return image


def to_jpeg_data_url(image_base64: str, max_side: int) -> str:
    """base64 이미지를 긴 변이 max_side 이하가 되게 줄여 JPEG data URL로 바꾼다.

    OpenAI에 이미지를 보낼 때 크기와 전송량을 줄이는 데 쓴다.

    Args:
        image_base64: 이미지의 base64 문자열 (PNG 등 PIL이 읽을 수 있는 형식).
        max_side: 결과 이미지의 긴 변 최대 길이 (px).

    Returns:
        str: data:image/jpeg;base64,... 형식의 문자열.

    Raises:
        ValueError: 이미지를 읽을 수 없을 때.
    """
    image = decode_base64_image(image_base64).convert("RGB")
    image.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"
