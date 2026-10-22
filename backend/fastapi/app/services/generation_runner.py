"""이미지 생성을 실행하고 측정 로그를 남기는 서비스.

생성일자: 2026-10-22
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

import json
import threading
import time
from datetime import datetime

from app.core.config import settings
from app.services.gpu_out_of_memory_error import GpuOutOfMemoryError
from app.services.image_generator import ImageGenerator
from app.utils.gpu import get_peak_vram_mb, reset_peak_vram

# VRAM 최대 사용량이 다른 요청과 섞이지 않도록 생성은 한 번에 하나씩 실행한다
_lock = threading.Lock()


def run_generation(
    image_generator: ImageGenerator,
    prompt: str,
    width: int,
    height: int,
    seeds: list[int],
) -> list[str]:
    """이미지를 생성하고 소요 시간과 VRAM 최대 사용량을 로그 파일에 기록한다.

    Args:
        image_generator: 이미지 생성기.
        prompt: 영어 프롬프트.
        width: 이미지 너비.
        height: 이미지 높이.
        seeds: 이미지마다 사용할 seed 목록.

    Returns:
        list[str]: seeds 순서대로 생성한 PNG 이미지의 base64 문자열 목록.

    Raises:
        GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
    """
    with _lock:
        requested_at = datetime.now().astimezone()
        reset_peak_vram()
        started = time.perf_counter()
        status = "error"
        try:
            images = image_generator.generate(prompt, width, height, seeds)
            status = "success"
            return images
        except GpuOutOfMemoryError:
            status = "out_of_memory"
            raise
        finally:
            elapsed = time.perf_counter() - started
            vram_allocated_mb, vram_reserved_mb = get_peak_vram_mb()
            _write_log(
                {
                    "requested_at": requested_at.isoformat(timespec="seconds"),
                    "status": status,
                    "image_generator": settings.image_generator,
                    "num_images": len(seeds),
                    "width": width,
                    "height": height,
                    # offload 설정은 sdxl 생성기에서만 쓴다
                    "sdxl_use_offload": (
                        settings.sdxl_use_offload
                        if settings.image_generator == "sdxl"
                        else None
                    ),
                    "elapsed_seconds": round(elapsed, 2),
                    "vram_peak_allocated_mb": vram_allocated_mb,
                    "vram_peak_reserved_mb": vram_reserved_mb,
                }
            )


def _write_log(record: dict) -> None:
    """GENERATION_LOG_PATH가 설정되어 있으면 로그를 JSONL 한 줄로 추가한다.

    Args:
        record: 기록할 로그 항목.
    """
    path = settings.generation_log_path
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
