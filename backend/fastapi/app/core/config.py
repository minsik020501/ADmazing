"""환경 변수 기반 애플리케이션 설정.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """.env 및 환경 변수에서 읽어오는 애플리케이션 설정."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=("settings_",)
    )

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    cors_origins: list[str] = ["http://localhost:12000"]

    image_generator: Literal["mock", "diffusers"] = "mock"
    model_path: str = "stabilityai/sdxl-turbo"
    lora_path: str | None = None
    num_inference_steps: int = 4
    guidance_scale: float = 0.0
    default_image_width: int = 512
    default_image_height: int = 512
    hf_token: str | None = None


settings = Settings()
