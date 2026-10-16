# backend/ai

광고 이미지 모델의 학습·실험 코드입니다. 서버로 실행되지 않으며, 학습 결과물은 루트의 `models/` 폴더에 저장되고 backend(FastAPI)가 이를 불러와 사용합니다.

## 산출물 규칙

```
models/<name>/
├── model_index.json ...               # 전체 모델일 때 → MODEL_PATH=/models/<name>
├── pytorch_lora_weights.safetensors   # LoRA일 때     → LORA_PATH=/models/<name>
└── metadata.json                      # base_model, 학습 설정 등
```

- 가중치는 git에 올리지 않습니다. 팀 공유는 공용 스토리지를 지정해 사용합니다.
- 노트북 실험은 `notebooks/`에 둡니다. 아래 [노트북](#노트북) 규칙을 따릅니다.

## 실행

`--device`로 학습 디바이스를 선택합니다: `auto`(기본, cuda → mps → cpu 순), `cuda`, `mps`, `cpu`

### Docker (cuda / cpu)

```bash
docker compose --profile train run --rm trainer python train.py --name ad-lora-v1
```

### macOS 로컬 (mps)

Docker 컨테이너에서는 Apple GPU(Metal)에 접근할 수 없으므로 MPS는 macOS에서 직접 실행해야 합니다.

```bash
cd backend/ai
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python train.py --name ad-lora-v1 --device mps --output-root ../../models
```

## 노트북

| 경로 | git | 용도 |
|:--|:--|:--|
| `notebooks/` | 포함 | 팀에 공유할 실험 (설정·결과 기록) |
| `notebooks/scratch/` | 제외 | 개인 실험용 |

노트북 출력(생성 이미지 등)은 커밋하지 않습니다. 저장소를 clone한 뒤 한 번만 아래를 실행하면 커밋 시 출력이 자동으로 제거됩니다.

```bash
pip install -r backend/requirements-dev.txt
nbstripout --install   # 저장소 루트에서 실행
```

공유할 실험 결과(이미지, 지표 등)는 노트북 출력 대신 마크다운 셀에 요약하거나 공유 드라이브에 올리고 링크를 남깁니다.
