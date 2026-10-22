"""CUDA VRAM 사용량 측정 유틸리티.

torch가 없거나(mock 환경) CUDA를 쓸 수 없으면 아무것도 하지 않는다.

생성일자: 2026-10-22
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""


def _cuda_torch():
    """CUDA를 사용할 수 있을 때만 torch 모듈을 반환한다.

    Returns:
        module | None: torch 모듈. torch가 없거나 CUDA를 쓸 수 없으면 None.
    """
    try:
        import torch
    except ImportError:
        return None
    return torch if torch.cuda.is_available() else None


def reset_peak_vram() -> None:
    """VRAM 최대 사용량 통계를 초기화한다."""
    torch = _cuda_torch()
    if torch is not None:
        torch.cuda.reset_peak_memory_stats()


def get_peak_vram_mb() -> tuple[float | None, float | None]:
    """마지막 초기화 이후 VRAM 최대 사용량을 MB 단위로 조회한다.

    Returns:
        tuple[float | None, float | None]: (텐서 최대 할당량, 최대 예약량).
            예약량은 nvidia-smi에 보이는 값에 가깝다. CUDA가 아니면 (None, None).
    """
    torch = _cuda_torch()
    if torch is None:
        return None, None
    mb = 1024 * 1024
    return (
        round(torch.cuda.max_memory_allocated() / mb, 1),
        round(torch.cuda.max_memory_reserved() / mb, 1),
    )
