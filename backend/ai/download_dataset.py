"""Pitt Ads 이미지 데이터셋을 backend/ai/data/ 폴더에 내려받는다.

출처: https://huggingface.co/datasets/Mindykkyan/PittadsDB-AdsPics
원본: https://people.cs.pitt.edu/~kovashka/ads/ (연구용 데이터셋, 상업적 사용 주의)

이미지는 images/0 ~ images/10 하위 폴더에 나뉘어 있다 (총 64,832장, 약 12GB).
용량이 커서 Git에 올리지 않는다. 각자 이 스크립트를 실행해서 로컬에 받는다.
이미 받은 파일은 건너뛰므로 중단돼도 다시 실행하면 이어서 받는다.
HF_TOKEN(환경변수 또는 레포 루트 .env)이 있으면 요청 제한이 완화된다.

실행 (레포 루트에서):
    python backend/ai/download_dataset.py                    # 주석 + 전체 이미지
    python backend/ai/download_dataset.py --subfolders 0 1   # 주석 + 0, 1번 폴더만
    python backend/ai/download_dataset.py --annotations-only # 주석만

생성일자: 2026-10-27
생성자: ven_choi
수정일자: 2026-10-27
수정자: ven_choi
"""

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv가 없으면 이미 설정된 환경변수만 쓴다
    load_dotenv = None

REPO_ROOT = Path(__file__).resolve().parents[2]

if load_dotenv is not None:
    # 이미 설정된 환경변수(예: Docker)는 덮어쓰지 않는다
    load_dotenv(REPO_ROOT / ".env")

# 이 파일 위치: backend/ai/download_dataset.py -> backend/ai/data/
DATA_DIR = Path(__file__).resolve().parent / "data"

DATASET_REPO = "Mindykkyan/PittadsDB-AdsPics"
DATASET_DIR = DATA_DIR / "pitt-ads"

SUBFOLDERS = [str(i) for i in range(11)]

# 이미지 주석(주제·감정·슬로건 등)과 카테고리 메타데이터. 영상·zip 원본은 받지 않는다.
ANNOTATION_PATTERNS = [
    "README.md",
    "docs/readme_images.txt",
    "image_annotations/image/*",
    "metadata/*",
]


def parse_args() -> argparse.Namespace:
    """커맨드라인 인자를 파싱한다.

    Returns:
        argparse.Namespace: 받을 이미지 하위 폴더 목록, 주석만 받을지 여부.
    """
    parser = argparse.ArgumentParser(description="Pitt Ads 데이터셋 다운로드")
    parser.add_argument(
        "--subfolders",
        nargs="+",
        choices=SUBFOLDERS,
        default=SUBFOLDERS,
        help="받을 이미지 하위 폴더 번호 (기본: 전체 0~10)",
    )
    parser.add_argument(
        "--annotations-only",
        action="store_true",
        help="이미지 없이 주석·메타데이터만 받는다",
    )
    return parser.parse_args()


def download(subfolders: list[str], annotations_only: bool) -> None:
    """주석과 선택한 하위 폴더의 이미지를 DATASET_DIR에 받는다.

    Args:
        subfolders: 받을 이미지 하위 폴더 번호 목록.
        annotations_only: True면 이미지는 받지 않는다.
    """
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    patterns = list(ANNOTATION_PATTERNS)
    if not annotations_only:
        patterns += [f"images/{name}/*" for name in subfolders]

    # .env의 "HF_TOKEN=" 처럼 빈 값이면 익명으로 받는다
    token = os.getenv("HF_TOKEN") or None
    if token:
        print("HF_TOKEN: 사용")
    elif load_dotenv is None:
        print("HF_TOKEN: 없음 (python-dotenv 미설치로 .env를 읽지 못함)")
    else:
        print("HF_TOKEN: 없음 (익명 요청, 요청 제한이 낮음)")

    snapshot_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        local_dir=DATASET_DIR,
        allow_patterns=patterns,
        token=token,
    )
    print(f"다운로드 완료: {DATASET_DIR}")


if __name__ == "__main__":
    args = parse_args()
    download(args.subfolders, args.annotations_only)
