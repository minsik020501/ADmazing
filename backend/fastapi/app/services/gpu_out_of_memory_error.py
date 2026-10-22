"""이미지 생성 중 GPU 메모리 부족 예외.

생성일자: 2026-10-22
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""


class GpuOutOfMemoryError(Exception):
    """이미지 생성 중 GPU 메모리가 부족할 때 발생한다.

    라우터가 torch를 import하지 않고도 처리할 수 있도록 torch 예외를 감싼다.
    """
