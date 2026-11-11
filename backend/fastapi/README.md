# backend/fastapi

Admazing API 서버입니다 (:11000). 한국어 프롬프트 번역, 이미지 생성, 광고 문구 추천, 문구 배치 추천을 담당합니다. 이미지 생성 모델은 별도 서버 없이 프로세스 안에서 직접 불러옵니다.

## 실행

루트에서 `docker compose up --build`로 실행하는 것을 기본으로 합니다. API 문서는 http://localhost:11000/docs 에서 볼 수 있습니다.

- 설정은 루트 `.env`를 읽습니다. 항목별 설명은 [.env.example](../../.env.example)을 참고하세요.
- `app/` 폴더가 컨테이너에 마운트되어 코드를 고치면 서버가 자동으로 재시작됩니다.
- torch 등 무거운 의존성은 [requirements-ml.txt](requirements-ml.txt)에 있으며 `INSTALL_ML=true`로 빌드할 때만 설치됩니다.

## API

모든 경로는 `/api` 아래에 있습니다.

| 메서드 | 경로 | 설명 |
|:--|:--|:--|
| GET | `/health` | 서버 상태와 이미지 생성기 정보 |
| POST | `/jobs` | 이미지 생성 작업 등록 (작업 id 반환) |
| GET | `/jobs/{job_id}` | 작업 상태 조회 |
| GET | `/jobs/{job_id}/events` | 진행률, 결과를 SSE로 전달 |
| DELETE | `/jobs/{job_id}` | 생성 작업 취소 |
| POST | `/generate` | 이미지 생성 (진행률 없이 한 번에 응답) |
| POST | `/copy/recommend` | 이미지 1장의 광고 문구 다시 추천 |
| POST | `/layout/recommend` | 이미지와 문구로 배치 추천안 3~5개 생성 |

요청 검증 에러(422)의 메시지는 한국어로 바꿔 응답합니다. 문구 상자 JSON 형식은 [docs/text_layer_spec.md](../../docs/text_layer_spec.md)를 참고하세요.

## 구조

```
app/
├── main.py          # 앱 진입점. 시작 시 생성기, 추천기, 작업 저장소를 한 번만 만든다
├── api/
│   ├── deps.py      # app.state의 서비스를 꺼내는 의존성
│   └── routes/      # health, generate, jobs, copy_recommend, layout_recommend
├── cli/
│   └── prepare_zimage.py   # model-prep 서비스: Z-Image 양자화 모델 변환
├── core/            # 설정(config), 비율별 해상도, 문구 역할, 레이아웃 템플릿
├── schemas/         # 요청, 응답 Pydantic 모델 (파일당 클래스 하나)
├── services/        # 번역, 이미지 생성, 작업 실행, 문구, 배치 추천
└── utils/           # 색, 이미지, 디바이스, GPU, 양자화 등 공용 함수
```

### 이미지 생성

| `IMAGE_GENERATOR` | 구현 | 비고 |
|:--|:--|:--|
| `mock` (기본) | `MockImageGenerator` | torch 없이 더미 이미지 반환 |
| `zimage` | `ZImageImageGenerator` | Z-Image-Turbo. `ZIMAGE_QUANT`로 int8/fp8 양자화 |
| `sdxl` | `SdxlImageGenerator` | SDXL 기본 모델 + fp16 VAE |
| `diffusers` | `DiffusersImageGenerator` | `MODEL_PATH`, `LORA_PATH`의 모델 |

- 생성 작업은 `GenerationJobStore`에 보관되고, `generation_job_runner`가 백그라운드에서 `ad_image_service`의 흐름(번역 → 생성 → 이미지별 문구 추천 → 응답 조립)을 실행하며 단계별 진행률을 기록합니다.
- GPU 작업은 `gpu_lock`으로 한 번에 하나씩 실행하고, VRAM 부족은 `GpuOutOfMemoryError`로 알립니다.
- `GENERATION_LOG_PATH`를 지정하면 요청마다 소요 시간, VRAM 최대 사용량을 JSONL로 남깁니다.

### 문구 추천

- `COPY_RECOMMENDER=openai`: 이미지(긴 변 `COPY_IMAGE_MAX_SIDE`px로 축소)와 프롬프트를 OpenAI에 보내 제목, 부제, 본문 문구를 역할별로 추천하고 강조색을 함께 고릅니다.
- `COPY_RECOMMENDER=mock`: OpenAI 없이 고정 문구를 반환합니다 (개발용).
- 요청의 `keywords`(최대 3개)는 모든 문구에 글자 그대로 들어갑니다. 이미지 1장이 `COPY_TIMEOUT_SECONDS`를 넘기면 그 이미지만 `copies_error`로 응답합니다.

### 문구 배치 추천

`TemplateLayoutRecommender`가 광고 레이아웃 템플릿과 규칙으로 위치, 글꼴, 색을 정합니다 (CPU, LLM 없음).

- `subject_detector`가 U²-Net(주 피사체)과 YuNet(얼굴)으로 가리면 안 되는 영역을 찾아 피합니다. 모델 파일이 없으면 `LAYOUT_DETECT_SUBJECTS=0`으로 끕니다.
- `layout_palette`가 문구 추천에서 받은 강조색과 문구 아래 배경의 색조로 배색을 정하고, 글자 영역 픽셀을 보고 명도 대비(제목 3:1, 본문 4.5:1)를 맞춥니다.

## 개발

```bash
pip install -r backend/requirements-dev.txt
black backend        # 코드 수정 후 포맷팅 (루트에서 실행)
```

- 주석은 Google style docstring(`Args:`, `Returns:`, `Raises:`)을 씁니다.
- 파일 머리말과 나머지 규칙은 [docs/project_code_rule.md](../../docs/project_code_rule.md)를 따릅니다.
