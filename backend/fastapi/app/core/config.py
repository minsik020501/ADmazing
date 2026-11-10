"""환경 변수 기반 애플리케이션 설정.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-11-06
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

    image_generator: Literal["mock", "diffusers", "sdxl", "zimage"] = "mock"
    model_path: str = "stabilityai/sdxl-turbo"
    lora_path: str | None = None
    num_inference_steps: int = 4
    guidance_scale: float = 0.0
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

    # IMAGE_GENERATOR=zimage 일 때 사용 (경로는 api 컨테이너 기준)
    zimage_device: Literal["auto", "cuda", "mps", "cpu"] = "auto"
    # 오프로드는 모델 전체(bf16 약 19GB)를 CPU 램에 두므로 램이 그보다 클 때만 켠다
    zimage_use_offload: bool = False
    # 모델 카드 권장값: 9 step (실제 DiT forward는 8번)
    zimage_steps: int = 9
    zimage_model_dir: Path = Path("/models/z-image-turbo")
    # none: 원본 bf16. int8, fp8: transformer·text_encoder를 8bit로 줄인 모델(cuda 전용).
    # 양자화 모델은 model-prep(app/cli/prepare_zimage.py)이 <zimage_model_dir>-<종류>에 만든다
    zimage_quant: Literal["none", "int8", "fp8"] = "none"

    # 생성된 이미지마다 광고 문구를 추천한다. mock은 OpenAI 키 없이 고정 문구를 돌려준다
    copy_recommender: Literal["mock", "openai"] = "openai"
    # 문구 추천에 쓸 OpenAI 모델. 비워 두면 OPENAI_MODEL을 쓴다 (이미지 입력 지원 모델)
    copy_openai_model: str | None = None
    # 추론 모델(gpt-5 계열 이후)의 reasoning_effort. 비워 두면 보내지 않는다 (추론 모델이 아니면
    # 비워야 한다). 기본(medium)은 한 번에 11~23초가 걸려 시간 제한을 넘기므로 none을 권장한다
    copy_reasoning_effort: Literal["none", "low", "medium", "high"] | None = None
    # 이미지 1장의 문구 추천(재요청 포함)에 허용하는 최대 시간
    copy_timeout_seconds: float = Field(20.0, gt=0)
    # OpenAI에 보낼 이미지의 긴 변(px). 분위기·색감·피사체만 보면 되므로 줄여서 보낸다
    copy_image_max_side: int = Field(512, ge=64)

    # 문구 배치 추천은 템플릿과 규칙으로 만든다 (CPU). 가리면 안 되는 영역(제품, 얼굴)을
    # 전용 검출기로 찾아 피한다. 끄면 영역을 피하지 않는다 (모델 파일이 없는 개발 환경용)
    layout_detect_subjects: bool = True
    # 주 피사체 분리 U²-Net, 얼굴 검출 YuNet ONNX 파일
    layout_salient_model_path: Path = Path("/models/detectors/u2net.onnx")
    layout_face_model_path: Path = Path(
        "/models/detectors/face_detection_yunet_2023mar.onnx"
    )


settings = Settings()
