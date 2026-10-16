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

### 학습한 모델 사용

학습 산출물을 `models/<name>/`에 두고 `.env`에서 경로를 지정합니다. (컨테이너에는 `/models`로 마운트됨)

```bash
MODEL_PATH=/models/ad-v1         # 전체 모델
LORA_PATH=/models/ad-lora-v1     # 또는 기본 모델 + LoRA
```

산출물 형식과 학습 실행 방법은 [backend/ai/README.md](backend/ai/README.md)를 참고하세요.

