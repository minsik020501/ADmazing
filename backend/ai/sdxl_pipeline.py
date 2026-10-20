"""SDXL 기본 모델 + fp16 VAE로 영어 프롬프트에서 이미지를 생성한다.

8GB GPU(RTX 5060)를 기준으로 메모리 절약 옵션을 켠다.
모델은 처음 한 번만 불러오고 재사용한다.

테스트 실행 (레포 루트에서):
    python backend/ai/sdxl_pipeline.py
"""

import time
from functools import lru_cache
from pathlib import Path

import torch
from diffusers import AutoencoderKL, StableDiffusionXLPipeline
from PIL import Image

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
SDXL_DIR = MODELS_DIR / "sdxl-base"
VAE_DIR = MODELS_DIR / "sdxl-vae-fp16-fix"

DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, text, watermark, deformed"


@lru_cache(maxsize=1)
def load_pipeline() -> StableDiffusionXLPipeline:
    """파이프라인을 한 번만 로드해서 재사용한다."""
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA GPU를 찾을 수 없습니다. RTX 50 시리즈는 PyTorch를 "
            "cu128 이상 빌드로 설치해야 합니다."
        )
    if not SDXL_DIR.exists() or not VAE_DIR.exists():
        raise FileNotFoundError(
            "모델 파일이 없습니다. 먼저 `python backend/ai/download_model.py`를 실행하세요."
        )

    vae = AutoencoderKL.from_pretrained(VAE_DIR, torch_dtype=torch.float16)
    pipe = StableDiffusionXLPipeline.from_pretrained(
        SDXL_DIR,
        vae=vae,
        torch_dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
    )

    # 8GB 메모리 절약 옵션 (.to("cuda")와 함께 쓰지 않는다)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()
    return pipe


def generate(
    prompt_en: str,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    steps: int = 25,
    guidance_scale: float = 6.0,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
) -> Image.Image:
    """영어 프롬프트로 이미지 1장을 생성해 PIL 이미지로 반환한다."""
    pipe = load_pipeline()
    generator = None
    if seed is not None:
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


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent / "outputs"
    out_dir.mkdir(exist_ok=True)

    torch.cuda.reset_peak_memory_stats()
    start = time.time()
    image = generate(
        "a cozy cafe poster, warm light, latte on a wooden table",
        seed=42,
    )
    elapsed = time.time() - start

    image.save(out_dir / "test.png")
    peak_gb = torch.cuda.max_memory_allocated() / 1024**3
    print(f"생성 시간: {elapsed:.1f}초 / 피크 VRAM: {peak_gb:.2f}GB")
    print(f"저장 위치: {out_dir / 'test.png'}")
