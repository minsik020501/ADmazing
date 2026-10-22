"""환경 변수 기반 애플리케이션 설정.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """.env 및 환경 변수에서 읽어오는 애플리케이션 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        protected_namespaces=("settings_",),
        # .env에서 값을 비워 두면(KEY=) 기본값을 쓴다
        env_ignore_empty=True,
    )

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    cors_origins: list[str] = ["http://localhost:12000"]

    image_generator: Literal["mock", "diffusers", "sdxl"] = "mock"
    model_path: str = "stabilityai/sdxl-turbo"
    lora_path: str | None = None
    num_inference_steps: int = 4
    guidance_scale: float = 0.0
    default_image_width: int = 512
    default_image_height: int = 512
    hf_token: str | None = None
    # 한 번의 요청에서 생성할 이미지 장수
    num_images_per_request: int = Field(4, ge=1)
    # 생성 요청마다 측정 로그(JSONL)를 남길 파일 경로. 비워 두면 기록하지 않는다
    generation_log_path: Path | None = None

    # IMAGE_GENERATOR=sdxl 일 때 사용 (경로는 api 컨테이너 기준)
    sdxl_device: Literal["auto", "cuda", "mps", "cpu"] = "auto"
    sdxl_use_offload: bool = True
    sdxl_steps: int = 25
    sdxl_guidance_scale: float = 6.0
    sdxl_negative_prompt: str = "blurry, low quality, text, watermark, deformed"
    sdxl_model_dir: Path = Path("/models/sdxl-base")
    sdxl_vae_dir: Path = Path("/models/sdxl-vae-fp16-fix")


settings = Settings()
