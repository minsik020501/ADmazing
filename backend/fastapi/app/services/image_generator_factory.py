"""설정에 따라 이미지 생성기를 생성하는 팩토리.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-20
수정자: ven_choi
"""

from app.core.config import settings
from app.services.image_generator import ImageGenerator
from app.services.mock_image_generator import MockImageGenerator


def create_image_generator() -> ImageGenerator:
    """IMAGE_GENERATOR 설정에 맞는 이미지 생성기를 생성한다.

    Returns:
        ImageGenerator: mock이면 MockImageGenerator, diffusers면 DiffusersImageGenerator,
            sdxl이면 SdxlImageGenerator.
    """
    if settings.image_generator == "sdxl":
        # torch가 설치되지 않은 mock 환경에서도 import 되도록 지연 import
        from app.services.sdxl_image_generator import SdxlImageGenerator

        return SdxlImageGenerator()
    if settings.image_generator == "diffusers":
        # torch가 설치되지 않은 mock 환경에서도 import 되도록 지연 import
        from app.services.diffusers_image_generator import DiffusersImageGenerator

        return DiffusersImageGenerator()
    return MockImageGenerator()
