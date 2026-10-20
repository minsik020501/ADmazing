"""SDXL 기본 모델 + fp16 VAE로 영어 프롬프트에서 이미지를 생성한다.

설정은 .env(또는 환경변수)로 바꿀 수 있다. 값이 없으면 아래 기본값을 쓴다.

    SDXL_DEVICE=auto            auto(cuda → mps → cpu 순), cuda, mps, cpu
    SDXL_USE_OFFLOAD=1          cuda 전용. 1: 오프로드(GPU 계산 + CPU 램 보관), 0: GPU 전용
    SDXL_STEPS=25               생성 step 수
    SDXL_GUIDANCE_SCALE=6.0     프롬프트 반영 강도
    SDXL_WIDTH=1024             이미지 가로 (8의 배수)
    SDXL_HEIGHT=1024            이미지 세로 (8의 배수)
    SDXL_NEGATIVE_PROMPT=...    그리지 말아야 할 것
    SDXL_MODEL_DIR=...          SDXL 기본 모델 폴더 (상대 경로는 레포 루트 기준)
    SDXL_VAE_DIR=...            fp16 VAE 폴더

디바이스별 메모리 설정:
    - cuda: SDXL_USE_OFFLOAD에 따라 오프로드 또는 GPU 전용
    - mps: Apple Silicon 통합 메모리에 올리고 attention slicing을 켠다
    - cpu: float32로 실행한다 (매우 느림, 동작 확인용)

함수 인자로 값을 직접 넘기면 .env 값보다 우선한다.
.env는 서버를 시작할 때 한 번 읽으므로, 값을 바꾸면 다시 시작해야 한다.

테스트 실행 (레포 루트에서):
    python backend/ai/sdxl_pipeline.py                  # .env 설정대로
    python backend/ai/sdxl_pipeline.py --device mps     # 디바이스 지정
    python backend/ai/sdxl_pipeline.py --offload        # 오프로드 강제 (cuda)
    python backend/ai/sdxl_pipeline.py --no-offload     # GPU 전용 강제 (cuda)

생성일자: 2026-10-20
생성자: ven_choi
수정일자: 2026-10-20
수정자: ven_choi
"""

import argparse
import os
import time
from functools import lru_cache
from pathlib import Path

import torch
from diffusers import AutoencoderKL, StableDiffusionXLPipeline
from PIL import Image

from device import DEVICE_CHOICES, resolve_device

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv가 없으면 이미 설정된 환경변수만 쓴다
    load_dotenv = None

REPO_ROOT = Path(__file__).resolve().parents[2]

if load_dotenv is not None:
    # 이미 설정된 환경변수(예: Docker)는 덮어쓰지 않는다
    load_dotenv(REPO_ROOT / ".env")


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value is None or value.strip() == "" else value.strip()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name}는 정수여야 합니다: {value!r}") from exc


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name}는 숫자여야 합니다: {value!r}") from exc


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    path = Path(value.strip())
    return path if path.is_absolute() else REPO_ROOT / path


# 기본값 (.env로 바꿀 수 있다)
MODELS_DIR = REPO_ROOT / "models"
SDXL_DIR = _env_path("SDXL_MODEL_DIR", MODELS_DIR / "sdxl-base")
VAE_DIR = _env_path("SDXL_VAE_DIR", MODELS_DIR / "sdxl-vae-fp16-fix")

DEFAULT_DEVICE = _env_str("SDXL_DEVICE", "auto")
DEFAULT_USE_OFFLOAD = _env_bool("SDXL_USE_OFFLOAD", True)
DEFAULT_STEPS = _env_int("SDXL_STEPS", 25)
DEFAULT_GUIDANCE_SCALE = _env_float("SDXL_GUIDANCE_SCALE", 6.0)
DEFAULT_WIDTH = _env_int("SDXL_WIDTH", 1024)
DEFAULT_HEIGHT = _env_int("SDXL_HEIGHT", 1024)
DEFAULT_NEGATIVE_PROMPT = _env_str(
    "SDXL_NEGATIVE_PROMPT", "blurry, low quality, text, watermark, deformed"
)

if DEFAULT_DEVICE not in DEVICE_CHOICES:
    raise ValueError(
        f"SDXL_DEVICE는 {', '.join(DEVICE_CHOICES)} 중 하나여야 합니다: "
        f"{DEFAULT_DEVICE!r}"
    )


@lru_cache(maxsize=2)
def load_pipeline(device: str, use_offload: bool = True) -> StableDiffusionXLPipeline:
    """파이프라인을 디바이스·모드별로 한 번만 로드해서 재사용한다.

    Args:
        device: 실행 디바이스 (cuda, mps, cpu). resolve_device로 확인한 값.
        use_offload: cuda에서 오프로드를 쓸지 여부. mps, cpu에서는 무시한다.

    Returns:
        StableDiffusionXLPipeline: 디바이스에 맞게 설정된 SDXL 파이프라인.

    Raises:
        FileNotFoundError: 모델 파일을 아직 내려받지 않았을 때.
    """
    if not SDXL_DIR.exists() or not VAE_DIR.exists():
        raise FileNotFoundError(
            "모델 파일이 없습니다. 먼저 `python backend/ai/download_model.py`를 실행하세요.\n"
            f"찾은 경로: {SDXL_DIR}, {VAE_DIR}"
        )

    # CPU는 fp16 연산을 제대로 지원하지 않아서 float32로 올린다
    dtype = torch.float32 if device == "cpu" else torch.float16

    vae = AutoencoderKL.from_pretrained(VAE_DIR, torch_dtype=dtype)
    pipe = StableDiffusionXLPipeline.from_pretrained(
        SDXL_DIR,
        vae=vae,
        torch_dtype=dtype,
        variant="fp16",
        use_safetensors=True,
    )

    if device == "cuda" and use_offload:
        # 계산은 GPU, 쓰지 않는 부품은 CPU 램에 보관 (.to("cuda")와 함께 쓰지 않는다)
        pipe.enable_model_cpu_offload()
    else:
        # 모델 전체를 디바이스에 올린다
        pipe.to(device)
        if device == "mps":
            # 통합 메모리 64GB 미만 Mac에서 메모리 피크를 낮춘다
            pipe.enable_attention_slicing()

    pipe.vae.enable_tiling()
    return pipe


def generate(
    prompt_en: str,
    negative_prompt: str | None = None,
    steps: int | None = None,
    guidance_scale: float | None = None,
    width: int | None = None,
    height: int | None = None,
    seed: int | None = None,
    use_offload: bool | None = None,
    device: str | None = None,
) -> Image.Image:
    """영어 프롬프트로 이미지 1장을 생성해 PIL 이미지로 반환한다.

    값을 넘기지 않으면(None) .env 설정 또는 기본값을 쓴다.

    Args:
        prompt_en: 영어 프롬프트.
        negative_prompt: 피하고 싶은 요소를 적은 네거티브 프롬프트.
        steps: 디노이징 스텝 수.
        guidance_scale: 프롬프트를 얼마나 강하게 따를지 정하는 값.
        width: 이미지 너비 (px, 8의 배수).
        height: 이미지 높이 (px, 8의 배수).
        seed: 결과를 재현할 때 쓰는 시드. None이면 매번 달라진다.
        use_offload: cuda에서 오프로드를 쓸지 여부.
        device: auto, cuda, mps, cpu 중 하나.

    Returns:
        Image.Image: 생성된 이미지.

    Raises:
        ValueError: 가로나 세로가 8의 배수가 아닐 때.
    """
    negative_prompt = (
        DEFAULT_NEGATIVE_PROMPT if negative_prompt is None else negative_prompt
    )
    steps = DEFAULT_STEPS if steps is None else steps
    guidance_scale = (
        DEFAULT_GUIDANCE_SCALE if guidance_scale is None else guidance_scale
    )
    width = DEFAULT_WIDTH if width is None else width
    height = DEFAULT_HEIGHT if height is None else height
    use_offload = DEFAULT_USE_OFFLOAD if use_offload is None else use_offload
    device = resolve_device(DEFAULT_DEVICE if device is None else device)

    if width % 8 != 0 or height % 8 != 0:
        raise ValueError(f"가로와 세로는 8의 배수여야 합니다: {width}x{height}")

    pipe = load_pipeline(device, use_offload)
    generator = None
    if seed is not None:
        # 난수 발생기는 CPU에 둔다 (디바이스와 상관없이 같은 seed면 같은 그림이 나오게)
        generator = torch.Generator(device="cpu").manual_seed(seed)

    result = pipe(
        prompt=prompt_en,
        negative_prompt=negative_prompt,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        generator=generator,
    )
    return result.images[0]


def _memory_usage(device: str) -> str:
    """디바이스별 메모리 사용량을 출력용 문자열로 만든다.

    Returns:
        str: cuda는 피크 VRAM, mps는 현재 할당된 메모리, cpu는 측정하지 않는다는 문구.
    """
    if device == "cuda":
        return f"피크 VRAM: {torch.cuda.max_memory_allocated() / 1024**3:.2f}GB"
    if device == "mps":
        return f"MPS 메모리: {torch.mps.driver_allocated_memory() / 1024**3:.2f}GB"
    return "메모리: 측정 안 함 (cpu)"


def _run_test(device: str, use_offload: bool | None) -> None:
    out_dir = Path(__file__).resolve().parent / "outputs"
    out_dir.mkdir(exist_ok=True)

    print(f"디바이스: {device}")
    if device == "cuda":
        resolved = DEFAULT_USE_OFFLOAD if use_offload is None else use_offload
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"모드: {'오프로드 (GPU 계산 + CPU 램 보관)' if resolved else 'GPU 전용'}"
        )
    print(
        f"설정: {DEFAULT_WIDTH}x{DEFAULT_HEIGHT}, steps={DEFAULT_STEPS}, "
        f"guidance={DEFAULT_GUIDANCE_SCALE}"
    )

    prompt = "a cozy cafe poster, warm light, latte on a wooden table"
    try:
        # 1회차: 모델 로딩과 준비 시간이 포함된다
        if device == "cuda":
            torch.cuda.reset_peak_memory_stats()
        start = time.time()
        image = generate(prompt, seed=42, use_offload=use_offload, device=device)
        first = time.time() - start
        memory = _memory_usage(device)

        # 2회차: 이미 로드된 상태의 순수 생성 시간
        start = time.time()
        generate(prompt, seed=43, use_offload=use_offload, device=device)
        second = time.time() - start
    except torch.cuda.OutOfMemoryError:
        print("GPU 메모리가 부족합니다. SDXL_USE_OFFLOAD=1(오프로드)로 실행하세요.")
        return

    image.save(out_dir / "test.png")
    print(f"1회차(로딩 포함): {first:.1f}초 / 2회차: {second:.1f}초")
    print(memory)
    print(f"저장 위치: {out_dir / 'test.png'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--device",
        choices=DEVICE_CHOICES,
        default=None,
        help="실행 디바이스 (지정하지 않으면 SDXL_DEVICE, 기본 auto)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--offload", action="store_true", help="오프로드 모드 강제")
    group.add_argument("--no-offload", action="store_true", help="GPU 전용 모드 강제")
    args = parser.parse_args()

    if args.offload:
        mode = True
    elif args.no_offload:
        mode = False
    else:
        mode = None  # .env 설정을 따른다
    _run_test(resolve_device(args.device or DEFAULT_DEVICE), use_offload=mode)
