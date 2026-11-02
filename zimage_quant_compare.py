"""Z-Image-Turbo 양자화 방식별 메모리, 속도, 품질을 비교하는 실험 스크립트.

V3 회의에서 정한 비교 구성을 같은 프롬프트와 seed로 돌려 이미지와 측정값을 저장한다.
    bf16      양자화 없음 (기준)
    te-int8   텍스트 인코더만 INT8
    te-fp8    텍스트 인코더만 FP8 (가중치만 FP8로 저장하고 계산은 bf16)
    all-int8  텍스트 인코더 + 트랜스포머 INT8
    all-fp8   텍스트 인코더 + 트랜스포머 FP8 (가중치만 FP8로 저장하고 계산은 bf16)

GPU 메모리가 24GB급인 서버에서 실행한다. bf16 기준은 가중치만 약 19GB라
8GB급 PC에서는 불러올 수 없다. 모델 폴더는 .env의 ZIMAGE_MODEL_DIR을 따른다.

실행 (레포 루트에서):
    python backend/ai/zimage_quant_compare.py --check            # 환경과 설정 객체 확인
    python backend/ai/zimage_quant_compare.py --mode bf16        # 기준 먼저
    python backend/ai/zimage_quant_compare.py --mode te-int8 te-fp8 all-int8 all-fp8
    python backend/ai/zimage_quant_compare.py --mode all         # 5개를 차례로

결과는 backend/ai/outputs/zimage_quant/ 아래에 저장한다.
    <모드>/p01_s42.png 형식의 이미지, results.jsonl 측정 기록


"""

import argparse
import json
import math
import os
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv가 없으면 이미 설정된 환경변수만 쓴다
    load_dotenv = None

REPO_ROOT = Path(__file__).resolve().parents[2]
if load_dotenv is not None:
    load_dotenv(REPO_ROOT / ".env")

MODES = ("bf16", "te-int8", "te-fp8", "all-int8", "all-fp8")
OUT_DIR = Path(__file__).resolve().parent / "outputs" / "zimage_quant"

# 짧은 영어 광고 프롬프트. 평가 세트를 쓰려면 --prompts-file로 한 줄에 하나씩 넘긴다
DEFAULT_PROMPTS = [
    "a latte in a ceramic cup on a wooden cafe table, warm window light, product photo",
    "freshly baked croissants on a rustic bakery counter, soft morning light, ad photo",
    "a bowl of Korean bibimbap on a dark wooden table, steam rising, food photography",
    "a small flower shop storefront with colorful bouquets, golden hour, advertising photo",
]


def _model_dir() -> Path:
    """Z-Image 모델 폴더를 .env 설정에서 찾는다.

    Returns:
        Path: ZIMAGE_MODEL_DIR (상대 경로는 레포 루트 기준), 없으면 models/z-image-turbo.
    """
    value = os.getenv("ZIMAGE_MODEL_DIR", "").strip() or "models/z-image-turbo"
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _steps() -> int:
    """생성 step 수를 .env의 ZIMAGE_STEPS에서 읽는다. 기본값은 서버와 같은 9."""
    value = os.getenv("ZIMAGE_STEPS", "").strip()
    return int(value) if value else 9


def _version(package: str) -> str:
    """설치된 패키지 버전을 문자열로 돌려준다."""
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "설치 안 됨"


def build_quant_config(mode: str):
    """모드에 맞는 파이프라인 양자화 설정을 만든다.

    Args:
        mode: MODES 중 하나.

    Returns:
        PipelineQuantizationConfig | None: bf16이면 None.

    Raises:
        ImportError: 필요한 양자화 라이브러리가 설치되지 않았을 때.
    """
    from diffusers import PipelineQuantizationConfig

    if mode == "bf16":
        return None

    components = (
        ["text_encoder"] if mode.startswith("te-") else ["transformer", "text_encoder"]
    )

    if mode.endswith("int8"):
        # bitsandbytes LLM.int8. diffusers와 transformers가 같은 인자를 쓴다
        return PipelineQuantizationConfig(
            quant_backend="bitsandbytes_8bit",
            quant_kwargs={"load_in_8bit": True},
            components_to_quantize=components,
        )

    # FP8: torchao의 가중치 전용 FP8. 구성요소마다 다른 설정 클래스를 써야 해서 mapping을 쓴다
    from diffusers import TorchAoConfig as DiffusersTorchAoConfig
    from torchao.quantization import Float8WeightOnlyConfig
    from transformers import TorchAoConfig as TransformersTorchAoConfig

    mapping = {"text_encoder": TransformersTorchAoConfig(Float8WeightOnlyConfig())}
    if "transformer" in components:
        mapping["transformer"] = DiffusersTorchAoConfig(Float8WeightOnlyConfig())
    return PipelineQuantizationConfig(quant_mapping=mapping)


def check() -> None:
    """모델을 불러오지 않고 환경과 양자화 설정 객체가 만들어지는지 확인한다."""
    import torch

    print("== 패키지 버전 ==")
    for package in (
        "torch",
        "diffusers",
        "transformers",
        "accelerate",
        "bitsandbytes",
        "torchao",
    ):
        print(f"{package:<14} {_version(package)}")

    print("\n== GPU ==")
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        capability = torch.cuda.get_device_capability(0)
        print(f"이름: {props.name}")
        print(f"VRAM: {props.total_memory / 1024**3:.1f}GB")
        print(f"compute capability: {capability[0]}.{capability[1]}")
        # 일반적으로 FP8 연산 하드웨어는 8.9(Ada) 이상에서 지원한다
        print(f"FP8 하드웨어 지원(8.9 이상): {capability >= (8, 9)}")
    else:
        print("CUDA GPU를 찾을 수 없습니다.")

    print("\n== 양자화 설정 객체 생성 (모델은 불러오지 않음) ==")
    for mode in MODES[1:]:
        try:
            build_quant_config(mode)
            print(f"{mode:<9} OK")
        except Exception as exc:  # 어떤 오류인지 그대로 보여 주려고 넓게 잡는다
            print(f"{mode:<9} 실패: {type(exc).__name__}: {exc}")

    print("\n== 모델 ==")
    model_dir = _model_dir()
    print(f"{model_dir} 존재: {model_dir.exists()}")
    try:
        from diffusers import ZImagePipeline  # noqa: F401

        print("ZImagePipeline import: OK")
    except Exception as exc:
        print(f"ZImagePipeline import 실패: {type(exc).__name__}: {exc}")


def _psnr(path_a: Path, path_b: Path) -> float:
    """두 이미지의 PSNR(dB)을 계산한다. 같은 이미지면 무한대."""
    import numpy as np
    from PIL import Image

    a = np.asarray(Image.open(path_a).convert("RGB"), dtype=np.float64)
    b = np.asarray(Image.open(path_b).convert("RGB"), dtype=np.float64)
    mse = float(np.mean((a - b) ** 2))
    return math.inf if mse == 0 else 10 * math.log10(255.0**2 / mse)


def run_mode(mode: str, args: argparse.Namespace) -> None:
    """한 가지 모드로 모델을 불러와 이미지를 만들고 측정값을 저장한다.

    Args:
        mode: MODES 중 하나.
        args: 크기, seed, 배치 같은 실행 옵션.

    Raises:
        FileNotFoundError: 모델 폴더가 없을 때.
        RuntimeError: CUDA GPU가 없을 때.
    """
    import torch
    from diffusers import ZImagePipeline

    model_dir = _model_dir()
    if not model_dir.exists():
        raise FileNotFoundError(f"모델 폴더가 없습니다: {model_dir}")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU가 필요합니다. 서버에서 실행하세요.")

    prompts = DEFAULT_PROMPTS
    if args.prompts_file:
        lines = Path(args.prompts_file).read_text(encoding="utf-8").splitlines()
        prompts = [line.strip() for line in lines if line.strip()]

    steps = _steps()
    quant_config = build_quant_config(mode)

    torch.cuda.empty_cache()
    start = time.time()
    pipe = ZImagePipeline.from_pretrained(
        model_dir,
        torch_dtype=torch.bfloat16,
        device_map="cuda",
        quantization_config=quant_config,
    )
    # 서버(zimage_image_generator.py)와 같은 VAE 설정
    pipe.vae.enable_slicing()
    pipe.vae.enable_tiling()
    pipe.vae.tile_sample_min_size = 512
    pipe.vae.tile_latent_min_size = 64
    load_sec = time.time() - start
    weights_gb = torch.cuda.memory_allocated() / 1024**3
    print(f"[{mode}] 로딩 {load_sec:.1f}초, 가중치 VRAM {weights_gb:.2f}GB")

    def generate(prompt: str, seeds: list[int]):
        generators = [torch.Generator(device="cpu").manual_seed(s) for s in seeds]
        return pipe(
            prompt=prompt,
            num_inference_steps=steps,
            guidance_scale=0.0,  # Turbo 모델은 CFG 없이 쓴다 (서버와 동일)
            width=args.width,
            height=args.height,
            num_images_per_prompt=len(seeds),
            generator=generators,
        ).images

    if not args.no_warmup:
        # 첫 호출은 커널 준비 때문에 느리므로 기록하지 않는다
        generate(prompts[0], [0])

    out_dir = OUT_DIR / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / "results.jsonl"
    elapsed_list: list[float] = []
    peak_list: list[float] = []

    for index, prompt in enumerate(prompts, start=1):
        for seed in args.seeds:
            seed_list = [seed + offset for offset in range(args.batch)]
            torch.cuda.reset_peak_memory_stats()
            start = time.time()
            record = {
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "mode": mode,
                "prompt_index": index,
                "seed": seed,
                "batch": args.batch,
                "size": f"{args.width}x{args.height}",
                "steps": steps,
                "load_sec": round(load_sec, 2),
                "weights_vram_gb": round(weights_gb, 3),
            }
            try:
                images = generate(prompt, seed_list)
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                record["status"] = "oom"
            else:
                torch.cuda.synchronize()
                elapsed = time.time() - start
                peak = torch.cuda.max_memory_allocated() / 1024**3
                for s, image in zip(seed_list, images):
                    image.save(out_dir / f"p{index:02d}_s{s}.png")
                elapsed_list.append(elapsed)
                peak_list.append(peak)
                record.update(
                    status="ok",
                    elapsed_sec=round(elapsed, 2),
                    peak_vram_gb=round(peak, 3),
                )
            with log_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")

    if elapsed_list:
        print(
            f"[{mode}] 평균 {sum(elapsed_list) / len(elapsed_list):.1f}초/호출, "
            f"피크 VRAM 최대 {max(peak_list):.2f}GB"
        )
    else:
        print(f"[{mode}] 성공한 생성이 없습니다 (results.jsonl의 status 확인)")

    baseline = OUT_DIR / "bf16"
    if mode != "bf16" and baseline.exists():
        scores = [
            _psnr(path, baseline / path.name)
            for path in sorted(out_dir.glob("*.png"))
            if (baseline / path.name).exists()
        ]
        finite = [s for s in scores if math.isfinite(s)]
        if finite:
            print(
                f"[{mode}] bf16 대비 PSNR 평균 {sum(finite) / len(finite):.1f}dB "
                "(참고용 수치이며 사람 눈으로 보는 품질과 다를 수 있음)"
            )


def parse_args() -> argparse.Namespace:
    """커맨드라인 인자를 파싱한다.

    Returns:
        argparse.Namespace: 실행 옵션.
    """
    parser = argparse.ArgumentParser(description="Z-Image-Turbo 양자화 비교")
    parser.add_argument("--check", action="store_true", help="환경과 설정만 확인")
    parser.add_argument(
        "--mode", nargs="+", choices=(*MODES, "all"), help="비교할 모드 (all은 전부)"
    )
    parser.add_argument("--prompts-file", help="영어 프롬프트 파일 (한 줄에 하나)")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43])
    parser.add_argument("--batch", type=int, default=1, help="한 번에 만들 장수")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--no-warmup", action="store_true", help="예열 호출 생략")
    args = parser.parse_args()

    if not args.check and not args.mode:
        parser.error("--mode 또는 --check가 필요합니다.")
    if args.width % 16 or args.height % 16:
        parser.error("가로와 세로는 16의 배수여야 합니다.")
    return args


def main() -> None:
    """옵션에 따라 환경 확인 또는 모드별 비교를 실행한다."""
    args = parse_args()
    if args.check:
        check()
        return

    modes = list(MODES) if "all" in args.mode else args.mode
    if len(modes) == 1:
        run_mode(modes[0], args)
        return

    # 모드마다 프로세스를 따로 띄워서 GPU 메모리가 서로 영향을 주지 않게 한다
    common = [
        "--seeds", *map(str, args.seeds),
        "--batch", str(args.batch),
        "--width", str(args.width),
        "--height", str(args.height),
    ]  # fmt: skip
    if args.prompts_file:
        common += ["--prompts-file", args.prompts_file]
    if args.no_warmup:
        common += ["--no-warmup"]
    for mode in modes:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--mode", mode, *common]
        )
        if result.returncode != 0:
            print(
                f"[{mode}] 실패 (종료 코드 {result.returncode}). 다음 모드로 넘어갑니다."
            )


if __name__ == "__main__":
    main()
