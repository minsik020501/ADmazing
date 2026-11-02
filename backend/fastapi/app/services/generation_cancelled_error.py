"""이미지 생성 취소 예외.

생성일자: 2026-11-02
생성자: ven_choi
수정일자: 2026-11-02
수정자: ven_choi
"""


class GenerationCancelledError(Exception):
    """사용자가 이미지 생성 작업을 취소했을 때 발생한다.

    생성 중에는 step 콜백에서 던져 파이프라인을 즉시 멈추는 데 쓴다.
    """
