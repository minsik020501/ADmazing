"""diffusers 파이프라인 step 콜백 유틸리티.

생성일자: 2026-11-02
생성자: ven_choi
수정일자: 2026-11-02
수정자: ven_choi
"""

from typing import Any, Callable

from app.services.image_generator import StepCallback


def to_step_end_callback(
    on_step: StepCallback | None,
) -> Callable[[Any, int, Any, dict], dict] | None:
    """진행 콜백을 diffusers의 callback_on_step_end 형식으로 감싼다.

    Args:
        on_step: (완료한 step 수, 전체 step 수)를 받는 콜백. 없으면 None.

    Returns:
        Callable | None: 파이프라인에 넘길 callback_on_step_end. on_step이 없으면 None.
    """
    if on_step is None:
        return None

    def callback(pipe: Any, step: int, timestep: Any, callback_kwargs: dict) -> dict:
        # step은 0부터 시작하므로 완료한 step 수는 step + 1이다
        on_step(step + 1, pipe.num_timesteps)
        return callback_kwargs

    return callback
