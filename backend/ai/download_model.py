"""비교할 모델의 가중치를 레포 루트의 models/ 폴더에 내려받는다.

가중치 파일은 용량이 커서 Git에 올리지 않는다.
서버나 각자의 PC에서 이 스크립트를 실행해 받는다.

실행 (레포 루트에서):
    python backend/ai/download_model.py --list                 # 받을 수 있는 모델 목록
    python backend/ai/download_model.py --model klein --dry-run  # 받기 전에 용량만 확인
    python backend/ai/download_model.py --model sdxl klein     # 두 모델 받기
    python backend/ai/download_model.py --model all            # sdxl + klein
    python backend/ai/download_model.py --model klein-base     # LoRA 학습용 base 모델

목록에 없는 후보 모델은 --repo로 받는다. 용량이 크니 --dry-run으로 먼저 확인한다.
    python backend/ai/download_model.py --repo Qwen/Qwen-Image --name qwen-image --dry-run
    python backend/ai/download_model.py --repo Qwen/Qwen-Image --name qwen-image \\
        --allow "*.json" "*.safetensors"

접근 제한(gated) 모델은 모델 페이지에서 약관에 동의하고 HF_TOKEN을 .env나 환경변수에
넣는다. 토큰은 코드나 채팅에 적지 않고 Git에 올리지 않는다.

생성일자: 2026-10-27
생성자: minsik51
수정일자: 2026-10-23
수정자: minsik51
"""

import argparse
import fnmatch
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

try:
    from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError
except ImportError:  # 구버전 huggingface_hub 호환
    from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv가 없으면 이미 설정된 환경변수만 쓴다
    load_dotenv = None

# 이 파일 위치: backend/ai/download_model.py -> 레포 루트의 models/
REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "models"

if load_dotenv is not None:
    # HF_TOKEN을 .env에 두면 huggingface_hub가 환경변수로 읽어서 쓴다
    load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class ModelSpec:
    """내려받을 저장소 하나에 대한 설정.

    Attributes:
        repo_id: Hugging Face 저장소 이름.
        local_dir: 받을 폴더.
        allow_patterns: 이 패턴에 맞는 파일만 받는다. None이면 모두 받는다.
        ignore_patterns: 이 패턴에 맞는 파일은 받지 않는다.
    """

    repo_id: str
    local_dir: Path
    allow_patterns: tuple[str, ...] | None = None
    ignore_patterns: tuple[str, ...] | None = None


# 저장소에는 diffusers 폴더와 단일 파일(flux-2-klein-*.safetensors)이 같이 있다.
# diffusers로 불러올 때는 단일 파일이 필요 없어서 제외한다.
KLEIN_IGNORE = ("flux-2-klein-*.safetensors",)

MODEL_SPECS: dict[str, tuple[ModelSpec, ...]] = {
    # SDXL 기본 모델은 fp16 가중치와 설정 파일만 받는다 (약 7GB)
    "sdxl": (
        ModelSpec(
            "stabilityai/stable-diffusion-xl-base-1.0",
            MODELS_DIR / "sdxl-base",
            allow_patterns=("*.json", "*.txt", "*.fp16.safetensors"),
        ),
        ModelSpec(
            "madebyollin/sdxl-vae-fp16-fix",
            MODELS_DIR / "sdxl-vae-fp16-fix",
            allow_patterns=("*.json", "*.safetensors"),
        ),
    ),
    "klein": (
        ModelSpec(
            "black-forest-labs/FLUX.2-klein-4B",
            MODELS_DIR / "flux2-klein-4b",
            ignore_patterns=KLEIN_IGNORE,
        ),
    ),
    # LoRA 학습은 증류하지 않은 base 모델로 한다 (비교 단계에서는 필요 없다)
    "klein-base": (
        ModelSpec(
            "black-forest-labs/FLUX.2-klein-base-4B",
            MODELS_DIR / "flux2-klein-base-4b",
            ignore_patterns=KLEIN_IGNORE,
        ),
    ),
}

# --model all로 받는 비교용 모델
COMPARE_MODELS = ("sdxl", "klein")
MODEL_CHOICES = (*MODEL_SPECS, "all")


def _fmt_size(num_bytes: int) -> str:
    """바이트 수를 읽기 쉬운 문자열로 바꾼다.

    Args:
        num_bytes: 바이트 수.

    Returns:
        str: 예) 1.5GB, 320.0MB.
    """
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def _is_selected(path: str, spec: ModelSpec) -> bool:
    """파일이 받을 대상인지 allow, ignore 패턴으로 판단한다.

    Args:
        path: 저장소 안의 파일 경로.
        spec: 받을 저장소 설정.

    Returns:
        bool: 받을 파일이면 True.
    """
    if spec.allow_patterns and not any(
        fnmatch.fnmatch(path, pattern) for pattern in spec.allow_patterns
    ):
        return False
    if spec.ignore_patterns and any(
        fnmatch.fnmatch(path, pattern) for pattern in spec.ignore_patterns
    ):
        return False
    return True


def list_files(spec: ModelSpec) -> list[tuple[str, int]]:
    """받을 파일과 크기를 저장소 정보에서 미리 읽는다 (파일은 받지 않는다).

    Args:
        spec: 받을 저장소 설정.

    Returns:
        list[tuple[str, int]]: (파일 경로, 바이트 수) 목록.

    Raises:
        GatedRepoError: 접근 권한이 필요한 저장소일 때.
        RepositoryNotFoundError: 저장소가 없거나 비공개일 때.
    """
    info = HfApi().model_info(spec.repo_id, files_metadata=True)
    return [
        (sibling.rfilename, sibling.size or 0)
        for sibling in info.siblings or []
        if _is_selected(sibling.rfilename, spec)
    ]


def download_one(spec: ModelSpec, dry_run: bool) -> None:
    """저장소 하나를 받는다. dry_run이면 받지 않고 용량만 보여 준다.

    Args:
        spec: 받을 저장소 설정.
        dry_run: True면 목록과 용량만 출력한다.

    Raises:
        OSError: 디스크 여유 공간이 부족할 때.
    """
    print(f"\n[{spec.repo_id}] -> {spec.local_dir}")
    files = list_files(spec)
    total = sum(size for _, size in files)
    print(f"  받을 파일 {len(files)}개, 약 {_fmt_size(total)}")

    free = shutil.disk_usage(MODELS_DIR).free
    print(f"  디스크 여유 공간: {_fmt_size(free)}")
    if total > free:
        raise OSError(
            f"디스크 공간이 부족합니다. 필요 {_fmt_size(total)}, 여유 {_fmt_size(free)}"
        )

    if dry_run:
        for path, size in sorted(files, key=lambda item: -item[1])[:10]:
            print(f"    {_fmt_size(size):>9}  {path}")
        return

    snapshot_download(
        repo_id=spec.repo_id,
        local_dir=spec.local_dir,
        allow_patterns=list(spec.allow_patterns) if spec.allow_patterns else None,
        ignore_patterns=list(spec.ignore_patterns) if spec.ignore_patterns else None,
    )
    print("  완료")


def download(
    models: list[str], extra: ModelSpec | None = None, dry_run: bool = False
) -> bool:
    """선택한 모델을 models/ 폴더에 내려받는다.

    Args:
        models: MODEL_SPECS의 이름 목록. all이 있으면 COMPARE_MODELS로 바꾼다.
        extra: --repo로 지정한 추가 저장소. 없으면 None.
        dry_run: True면 파일을 받지 않고 용량만 확인한다.

    Returns:
        bool: 모두 성공하면 True, 하나라도 실패하면 False.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    names: list[str] = []
    for name in models:
        names.extend(COMPARE_MODELS if name == "all" else (name,))
    specs = [spec for name in dict.fromkeys(names) for spec in MODEL_SPECS[name]]
    if extra is not None:
        specs.append(extra)

    failed = False
    for spec in specs:
        try:
            download_one(spec, dry_run)
        except GatedRepoError:
            failed = True
            print(
                f"  실패: {spec.repo_id}는 접근 권한이 필요합니다. 모델 페이지에서 "
                "약관에 동의하고 HF_TOKEN을 .env 또는 환경변수에 설정하세요."
            )
        except RepositoryNotFoundError:
            failed = True
            print(
                f"  실패: {spec.repo_id} 저장소를 찾을 수 없습니다. 이름을 확인하세요."
            )
        except OSError as exc:
            failed = True
            print(f"  실패: {exc}")

    if failed:
        print("\n일부 실패했습니다. 위 메시지를 확인하세요.")
    elif dry_run:
        print("\n확인 완료 (받지 않음)")
    else:
        print(f"\n다운로드 위치: {MODELS_DIR}")
    return not failed


def print_models() -> None:
    """받을 수 있는 모델 목록과 현재 받은 상태를 출력한다."""
    for name, specs in MODEL_SPECS.items():
        for spec in specs:
            done = spec.local_dir.exists() and any(spec.local_dir.iterdir())
            print(f"{name:<11} {spec.repo_id:<45} {'받음' if done else '없음'}")


def parse_args() -> argparse.Namespace:
    """커맨드라인 인자를 파싱한다.

    Returns:
        argparse.Namespace: 받을 모델과 옵션.
    """
    parser = argparse.ArgumentParser(description="모델 가중치 다운로드")
    parser.add_argument(
        "--model", nargs="+", choices=MODEL_CHOICES, default=[], help="받을 모델 이름"
    )
    parser.add_argument(
        "--repo", help="목록에 없는 Hugging Face 저장소 (예: Qwen/Qwen-Image)"
    )
    parser.add_argument("--name", help="--repo로 받을 때 models/ 아래 폴더 이름")
    parser.add_argument("--allow", nargs="+", help="--repo에서 받을 파일 패턴")
    parser.add_argument("--ignore", nargs="+", help="--repo에서 제외할 파일 패턴")
    parser.add_argument(
        "--dry-run", action="store_true", help="받지 않고 파일 수와 용량만 확인"
    )
    parser.add_argument("--list", action="store_true", help="받을 수 있는 모델 목록")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.list:
        print_models()
        sys.exit(0)

    extra = None
    if args.repo:
        folder = args.name or args.repo.split("/")[-1].lower()
        extra = ModelSpec(
            args.repo,
            MODELS_DIR / folder,
            allow_patterns=tuple(args.allow) if args.allow else None,
            ignore_patterns=tuple(args.ignore) if args.ignore else None,
        )

    # 아무것도 지정하지 않으면 지금까지처럼 SDXL만 받는다
    selected = args.model or ([] if extra else ["sdxl"])
    sys.exit(0 if download(selected, extra, args.dry_run) else 1)
