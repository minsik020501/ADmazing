"""SDXL 기본 모델과 fp16 VAE를 레포 루트의 models/ 폴더에 내려받는다.

가중치 파일은 용량이 커서 Git에 올리지 않는다.
각자 이 스크립트를 실행해서 로컬에 받는다.

실행 (레포 루트에서):
    python backend/ai/download_model.py
"""

from pathlib import Path

from huggingface_hub import snapshot_download

# 이 파일 위치: backend/ai/download_model.py -> 레포 루트의 models/
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"

SDXL_REPO = "stabilityai/stable-diffusion-xl-base-1.0"
SDXL_DIR = MODELS_DIR / "sdxl-base"

VAE_REPO = "madebyollin/sdxl-vae-fp16-fix"
VAE_DIR = MODELS_DIR / "sdxl-vae-fp16-fix"


def download() -> None:
    """fp16 가중치와 설정 파일만 받아서 용량을 줄인다 (약 7GB)."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=SDXL_REPO,
        local_dir=SDXL_DIR,
        allow_patterns=["*.json", "*.txt", "*.fp16.safetensors"],
    )
    snapshot_download(
        repo_id=VAE_REPO,
        local_dir=VAE_DIR,
        allow_patterns=["*.json", "*.safetensors"],
    )
    print(f"다운로드 완료: {MODELS_DIR}")


if __name__ == "__main__":
    download()
