# frontend

Admazing 웹 화면입니다 (:12000). React 18 + Vite + TypeScript로 만들었고, 텍스트 에디터 캔버스는 Konva(react-konva)를 씁니다. `/api` 요청은 Vite 프록시로 API 서버에 넘깁니다.

## 실행

루트에서 `docker compose up --build`로 실행하는 것을 기본으로 합니다. 로컬에서 따로 띄울 때는 아래처럼 실행합니다.

```bash
cd frontend
npm install
npm run dev          # http://localhost:12000, /api → http://localhost:11000
```

API 서버 주소는 `VITE_API_PROXY_TARGET`으로 바꿀 수 있습니다 (docker compose에서는 `http://api:11000`).

| 명령 | 설명 |
|:--|:--|
| `npm run dev` | 개발 서버 |
| `npm run build` | 타입 검사 + 빌드 (`dist/`) |
| `npm run preview` | 빌드 결과 미리보기 |
| `npm run format` | Prettier 포맷팅 (코드 수정 후 실행) |
| `npm run format:check` | 포맷팅 확인만 |

## 화면 구성

1. **입력**: 프롬프트, 예시 칩, 스타일, 비율 선택, 삽입할 문구(역할별 요청) 입력
2. **로딩**: 생성 진행률과 문구 추천 단계를 화면 전체에 표시하고 취소 가능
3. **결과**: 번역된 프롬프트, 옵션 요약, 이미지 격자, 크게 보기, 같은 옵션으로 다시 생성
4. **에디터**: 썸네일 줄에서 이미지를 고르고 캔버스에 문구 상자를 넣어 편집한 뒤 PNG로 저장
   - 글자 모양, 색(이미지 대표색 포함), 외곽선, 그림자, 배경 상자, 회전, 곡선
   - AI 추천 탭: 추천 문구 칩과 배치 추천안 선택
   - 되돌리기/다시 실행, 복사, 잘라내기, 붙여넣기, 맞춤 가이드, 방향키 이동, 여러 개 선택

서버 상태 배지와 라이트/다크 테마 전환은 화면 오른쪽 아래에 있습니다.

## 구조

```
src/
├── App.tsx              # 입력, 결과 화면과 에디터 전환
├── api/client.ts        # API 호출 (작업 등록, SSE 구독, 취소, 배치 추천, 헬스 체크)
├── components/
│   ├── common/          # Button, Chip, Modal, SectionLabel, AnimatedDots
│   ├── layout/          # Sidebar, ThemeToggle, ServerStatusBadge
│   ├── input/           # 프롬프트, 예시 칩, 스타일, 비율, 삽입할 문구, 생성 버튼
│   ├── loading/         # 생성 진행 화면
│   ├── result/          # 결과 영역, 이미지 크게 보기
│   └── editor/          # 에디터 화면, 캔버스, 문구 패널, 필드 부품, 맞춤, 곡선, 저장 유틸
├── constants/           # 예시 프롬프트, 스타일, 비율, 문구 역할, 폰트 목록(fonts.json)
├── hooks/               # useGeneration, useTextLayers, useCopyProposals, useFontsLoaded
└── styles/              # 디자인 토큰(tokens.css), 웹폰트(fonts.css)
```

- 문구 상자 JSON 형식은 [docs/text_layer_spec.md](../docs/text_layer_spec.md)를 따릅니다.
- `styles/fonts.css`와 `constants/fonts.json`은 `scripts/prepare_fonts.py`가 만드는 파일이므로 직접 고치지 않습니다. 폰트 파일은 `font-prep` 서비스가 `public/fonts/`로 제공합니다 (루트 [README](../README.md#광고-문구-폰트) 참고).
- 비율 값(`constants/imageRatios.ts`)은 서버의 `app/core/image_ratio.py`와 같아야 합니다.

## 개발 규칙

- 주석은 JSDoc(`@param name - 설명`, `@returns`, `@throws`)을 씁니다.
- 스타일은 CSS Modules(`*.module.css`)와 `tokens.css`의 토큰을 씁니다.
- ESLint는 쓰지 않고 Prettier(`.prettierrc.json`)로만 포맷팅합니다.
- 파일 머리말과 나머지 규칙은 [docs/project_code_rule.md](../docs/project_code_rule.md)를 따릅니다.
