"""ZIMAGE_QUANT에 맞는 Z-Image 양자화 모델이 없으면 원본(bf16)에서 변환해 저장한다.

docker compose의 model-prep 서비스가 api보다 먼저 한 번 실행한다. 이미 변환된 폴더가
있고 패키지 버전이 같으면 바로 끝난다. api 컨테이너는 /models를 읽기 전용으로 마운트하므로
변환은 쓰기 권한이 있는 이 명령에서만 한다.

변환은 부품(transformer, text_encoder)을 하나씩 GPU로 불러오면서 양자화하고 저장한 뒤
해제한다. 모델 전체(bf16 약 19GB)를 한꺼번에 올리지 않으므로 L4 24GB와 램이 적은
서버에서도 변환된다.

실행 (backend/fastapi에서):
    python -m app.cli.prepare_zimage

생성일자: 2026-11-04
생성자: ven_choi
수정일자: 2026-11-04
수정자: ven_choi
"""

import gc
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.utils.zimage_quant import (
    INFO_FILE,
    check_cuda,
    package_versions,
    quant_model_dir,
    stale_reason,
    torchao_quant_type,
)

# 양자화해서 저장하는 부품. 나머지(vae, tokenizer, scheduler)는 원본을 그대로 복사한다
QUANTIZED_COMPONENTS = ("transformer", "text_encoder")


def main() -> int:
    """설정을 확인하고 필요할 때만 양자화 모델을 만든다.

    Returns:
        int: 프로세스 종료 코드 (0: 성공 또는 할 일 없음, 1: 실패).
    """
    quant = settings.zimage_quant
    if settings.image_generator != "zimage" or quant == "none":
        print(
            f"[model-prep] 변환할 것이 없습니다 "
            f"(IMAGE_GENERATOR={settings.image_generator}, ZIMAGE_QUANT={quant})"
        )
        return 0

    source_dir = settings.zimage_model_dir
    target_dir = quant_model_dir(source_dir, quant)
    reason = stale_reason(target_dir, quant)
    if reason is None:
        print(f"[model-prep] 이미 변환된 모델을 씁니다: {target_dir}")
        return 0
    print(f"[model-prep] 변환을 시작합니다. 이유: {reason}")

    if not source_dir.exists():
        print(f"[model-prep] 원본 모델 폴더가 없습니다: {source_dir}", file=sys.stderr)
        return 1
    convert(source_dir, target_dir, quant)
    return 0


def convert(source_dir: Path, target_dir: Path, quant: str) -> None:
    """원본 모델을 양자화해 target_dir에 저장한다.

    임시 폴더에 모두 저장한 뒤 마지막에 이름을 바꾸므로, 중간에 멈춰도 target_dir에는
    완성된 모델만 남는다.

    Args:
        source_dir: 원본(bf16) 모델 폴더.
        target_dir: 양자화 모델을 저장할 폴더.
        quant: int8 또는 fp8.

    Raises:
        RuntimeError: CUDA를 쓸 수 없거나 fp8을 지원하지 않는 GPU일 때.
    """
    import torch

    check_cuda(torch, quant)
    start = time.perf_counter()
    work_dir = target_dir.with_name(target_dir.name + ".tmp")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    _quantize_transformer(torch, source_dir, work_dir, quant)
    _quantize_text_encoder(torch, source_dir, work_dir, quant)
    _copy_other_components(source_dir, work_dir)

    (work_dir / INFO_FILE).write_text(
        json.dumps(
            {
                "quant": quant,
                "method": f"torchao {type(torchao_quant_type(quant)).__name__}",
                "source": str(source_dir),
                "packages": package_versions(),
                "gpu": torch.cuda.get_device_name(),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    if target_dir.exists():
        # 버전이 바뀌어 다시 변환한 경우. 새 모델이 다 만들어진 뒤에 지운다
        shutil.rmtree(target_dir)
    work_dir.rename(target_dir)
    print(
        f"[model-prep] 변환 완료: {target_dir} "
        f"({time.perf_counter() - start:.0f}초, {_folder_gb(target_dir):.1f}GB)"
    )


def _quantize_transformer(torch, source_dir: Path, work_dir: Path, quant: str) -> None:
    """DiT를 불러오면서 양자화하고 저장한다."""
    from diffusers import TorchAoConfig, ZImageTransformer2DModel

    print("[model-prep] transformer 양자화 중", flush=True)
    model = ZImageTransformer2DModel.from_pretrained(
        source_dir,
        subfolder="transformer",
        torch_dtype=torch.bfloat16,
        quantization_config=TorchAoConfig(torchao_quant_type(quant)),
        # 가중치를 하나씩 GPU로 옮기며 양자화하므로 bf16 전체가 메모리에 올라가지 않는다
        device_map="cuda",
    )
    model.save_pretrained(work_dir / "transformer", safe_serialization=True)
    del model
    _free_gpu_memory(torch)


def _quantize_text_encoder(torch, source_dir: Path, work_dir: Path, quant: str) -> None:
    """텍스트 인코더(Qwen3)를 불러오면서 양자화하고 저장한다."""
    from transformers import AutoModel, TorchAoConfig

    print("[model-prep] text_encoder 양자화 중", flush=True)
    model = AutoModel.from_pretrained(
        source_dir / "text_encoder",
        dtype=torch.bfloat16,
        quantization_config=TorchAoConfig(torchao_quant_type(quant)),
        device_map="cuda",
    )
    model.save_pretrained(work_dir / "text_encoder", safe_serialization=True)
    del model
    _free_gpu_memory(torch)


def _copy_other_components(source_dir: Path, work_dir: Path) -> None:
    """양자화하지 않는 부품과 model_index.json을 원본에서 복사한다."""
    model_index = json.loads((source_dir / "model_index.json").read_text())
    for name in model_index:
        if name.startswith("_") or name in QUANTIZED_COMPONENTS:
            continue
        shutil.copytree(source_dir / name, work_dir / name)
    shutil.copy2(source_dir / "model_index.json", work_dir / "model_index.json")


def _free_gpu_memory(torch) -> None:
    """저장을 마치고 참조를 지운 부품의 GPU 메모리를 반환한다."""
    gc.collect()
    torch.cuda.empty_cache()


def _folder_gb(path: Path) -> float:
    """폴더 안 파일 크기의 합(GB)을 구한다.

    Returns:
        float: 폴더 크기 (GB).
    """
    return (
        sum(file.stat().st_size for file in path.rglob("*") if file.is_file()) / 1024**3
    )


if __name__ == "__main__":
    sys.exit(main())
