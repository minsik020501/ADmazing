"""라우터에서 사용하는 의존성 주입 함수.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

from fastapi import Request

from app.services.image_generator import ImageGenerator


def get_image_generator(request: Request) -> ImageGenerator:
    """서버 시작 시 로드된 이미지 생성기를 반환한다.

    Returns:
        ImageGenerator: app.state에 저장된 이미지 생성기.
    """
    return request.app.state.image_generator
