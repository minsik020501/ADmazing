# Admazing

텍스트 프롬프트(한국어)로 광고 이미지를 생성하는 프로젝트입니다.

## 구조

```
admazing/
├── backend/
│   ├── ai/          # 모델 학습·실험 코드 (서버 아님) → 산출물을 models/ 에 저장
│   └── fastapi/     # API 서버 (:11000) — 한→영 번역(OpenAI) + 이미지 생성(모델 직접 로드)
├── frontend/        # React + Vite + TypeScript (:12000)
├── models/          # 학습 산출물 (git 제외)
├── docker-compose.yml
└── docker-compose.gpu.yml   # NVIDIA GPU 환경용 override
```

## 요청 흐름

```
frontend ──POST /api/generate──▶ api ──OpenAI──▶ 영어 프롬프트
                                  │
                                  └── ImageGenerator(mock | diffusers) ──▶ PNG(base64)
                                          ▲
                              MODEL_PATH / LORA_PATH (HF 모델 또는 models/<name>)
```

## 실행

```bash
cp .env.example .env   # OPENAI_API_KEY 입력
docker compose up --build
```

- Frontend: http://localhost:12000
- API 문서: http://localhost:11000/docs

### 이미지 생성 모드

| 모드        | `.env` 설정                                    | 용도                                            |
|:------------|:-----------------------------------------------|:------------------------------------------------|
| mock (기본) | `IMAGE_GENERATOR=mock`, `INSTALL_ML=false`     | 프론트/백엔드 개발. torch 없이 더미 이미지 반환 |
| diffusers   | `IMAGE_GENERATOR=diffusers`, `INSTALL_ML=true` | 실제 모델로 생성 (시연·배포)                    |

diffusers 모드에서는 코드 변경으로 서버가 재시작될 때마다 모델을 다시 불러옵니다.

```bash
# NVIDIA GPU 서버
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

GPU 서버에서는 `.env`에 아래 줄을 넣어 두면 `-f` 없이 `docker compose up --build`만 해도 GPU 설정이 포함됩니다. 빠뜨리면 api 컨테이너가 GPU를 보지 못해 CPU로 생성하려다 램 부족으로 종료될 수 있습니다.

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.gpu.yml
SDXL_DEVICE=cuda      # GPU를 못 잡으면 CPU로 넘어가지 않고 바로 에러
ZIMAGE_DEVICE=cuda
```

#### Z-Image 양자화 (선택)

GPU 서버에서 `.env`에 `ZIMAGE_QUANT=fp8`(또는 `int8`)을 넣으면 transformer·text_encoder 가중치를 8bit로 줄여 올립니다. `fp8`은 SM 8.9 이상 GPU(L4 등)에서만 동작합니다.

`docker compose up` 시 api보다 먼저 `model-prep` 서비스가 실행되어, `models/z-image-turbo-<종류>/`가 없으면 `models/z-image-turbo/`에서 변환해 저장합니다. 첫 실행에만 변환 시간이 걸리고, 이후에는 바로 끝납니다. torch·torchao·diffusers·transformers 버전이 바뀌면 다시 변환합니다.

```bash
docker compose logs model-prep     # 변환 진행 상황 확인
```

컨테이너가 GPU를 보는지 확인:

```bash
docker compose exec api python -c "import torch; print(torch.cuda.is_available())"
```

### 광고 문구 폰트

`docker compose up` 시 frontend보다 먼저 `font-prep` 서비스가 실행되어 [fonts/manifest.json](fonts/manifest.json)의 폰트를 받아 woff2로 준비합니다. 폰트 파일은 git에 올리지 않고 Docker 볼륨(`font-files`)에 두며, frontend에서 `/fonts/...` 경로로 제공됩니다. 첫 실행에만 받는 시간이 걸리고, 받기에 실패해도 frontend는 뜹니다(해당 폰트만 기본 글꼴로 표시).

```bash
docker compose logs font-prep      # 준비 결과 확인
```

- 웹폰트 주소가 없는 폰트는 manifest에 `manual`로 적고, 배포처에서 직접 받아 `fonts/manual/<id>/`에 넣습니다.
- 폰트를 추가·변경하면 manifest를 고친 뒤 로컬에서 `python scripts/prepare_fonts.py`를 실행해 `frontend/src/styles/fonts.css`를 갱신하고 커밋합니다 (`pip install -r scripts/requirements.txt` 필요).

### 학습한 모델 사용

학습 산출물을 `models/<name>/`에 두고 `.env`에서 경로를 지정합니다. (컨테이너에는 `/models`로 마운트됨)

```bash
MODEL_PATH=/models/ad-v1         # 전체 모델
LORA_PATH=/models/ad-lora-v1     # 또는 기본 모델 + LoRA
```

산출물 형식과 학습 실행 방법은 [backend/ai/README.md](backend/ai/README.md)를 참고하세요.

