"""광고 이미지 모델 학습 스크립트.

산출물 규칙 (backend가 이 형식을 그대로 읽음):
    /models/<name>/
    ├── (전체 모델)  model_index.json + 하위 폴더   → MODEL_PATH=/models/<name>
    ├── (LoRA)      pytorch_lora_weights.safetensors → LORA_PATH=/models/<name>
    └── metadata.json   # base_model, 학습 설정, 날짜 등

사용 예:
    # Docker (cuda / cpu)
    docker compose --profile train run --rm trainer \
        python train.py --name ad-lora-v1 --base-model stabilityai/sdxl-turbo

    # macOS 로컬 (mps)
    python train.py --name ad-lora-v1 --device mps --output-root ../../models

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from device import DEVICE_CHOICES, resolve_device


def parse_args() -> argparse.Namespace:
    """커맨드라인 인자를 파싱한다.

    Returns:
        argparse.Namespace: 산출물 이름, 기본 모델, 산출물 루트 경로, 디바이스.
    """
    parser = argparse.ArgumentParser(description="Admazing 모델 학습")
    parser.add_argument("--name", required=True, help="산출물 이름 (/models/<name>)")
    parser.add_argument("--base-model", default="stabilityai/sdxl-turbo")
    parser.add_argument("--output-root", default="/models")
    parser.add_argument(
        "--device",
        choices=DEVICE_CHOICES,
        default="auto",
        help="학습 디바이스 (auto: cuda → mps → cpu 순으로 선택)",
    )
    return parser.parse_args()


def train(args: argparse.Namespace, output_dir: Path, device: str) -> None:
    """모델을 학습하고 산출물을 output_dir에 저장한다.

    Args:
        args: 커맨드라인 인자.
        output_dir: 산출물을 저장할 디렉터리.
        device: 학습 디바이스 (cuda, mps, cpu).

    Raises:
        NotImplementedError: 학습 로직이 아직 구현되지 않았다.
    """
    # TODO: 2단계에서 팀 회의 후 학습 방식(LoRA 등) 결정 후 구현
    #   - LoRA: pipe.save_lora_weights(output_dir, ...)
    #   - 전체 모델: pipe.save_pretrained(output_dir)
    #   - 모델과 텐서는 pipe.to(device) 로 디바이스에 올림
    #   - mps는 float16 학습이 불안정할 수 있으므로 float32 권장
    raise NotImplementedError("학습 로직이 아직 구현되지 않았습니다.")


def main() -> None:
    """학습을 실행하고 산출물 디렉터리에 metadata.json을 기록한다."""
    args = parse_args()
    device = resolve_device(args.device)
    print(f"학습 디바이스: {device}")

    output_dir = Path(args.output_root) / args.name
    output_dir.mkdir(parents=True, exist_ok=True)

    train(args, output_dir, device)

    metadata = {
        "name": args.name,
        "base_model": args.base_model,
        "device": device,
        "created_at": datetime.now().isoformat(),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
