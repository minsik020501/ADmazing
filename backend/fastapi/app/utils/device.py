"""생성에 사용할 디바이스 선택 유틸리티.

생성일자: 2026-10-28
생성자: ven_choi
수정일자: 2026-10-28
수정자: ven_choi
"""


def resolve_device(name: str) -> str:
    """요청한 디바이스가 사용 가능한지 확인하고 실제 사용할 디바이스를 결정한다.

    Args:
        name: auto, cuda, mps, cpu 중 하나. auto면 cuda → mps → cpu 순으로 선택한다.

    Returns:
        str: 실제 사용할 디바이스 이름 (cuda, mps, cpu).

    Raises:
        RuntimeError: 요청한 디바이스를 현재 환경에서 사용할 수 없을 때.
    """
    import torch

    available = {
        "cuda": torch.cuda.is_available(),
        "mps": torch.backends.mps.is_available(),
        "cpu": True,
    }
    if name == "auto":
        return next(device for device, ok in available.items() if ok)
    if not available[name]:
        raise RuntimeError(f"'{name}' 디바이스를 사용할 수 없습니다.")
    return name
