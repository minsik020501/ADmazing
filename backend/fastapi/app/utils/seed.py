"""이미지 생성 seed 유틸리티.

생성일자: 2026-10-22
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

import random

# torch.Generator와 다른 라이브러리에서도 안전하게 쓰도록 32비트 범위로 제한한다
MAX_SEED = 2**32 - 1


def make_seeds(seed: int | None, count: int) -> list[int]:
    """이미지마다 사용할 seed 목록을 만든다.

    Args:
        seed: 요청 seed. 있으면 seed부터 1씩 증가시키고, 없으면 랜덤으로 만든다.
        count: 생성할 이미지 장수.

    Returns:
        list[int]: 이미지 순서대로 사용할 seed 목록.
    """
    if seed is None:
        return [random.randint(0, MAX_SEED) for _ in range(count)]
    return [seed + i for i in range(count)]
