# Text layer spec

텍스트 에디터가 이미지 위에 그리는 **문구 상자(텍스트 레이어)**의 JSON 형식을 정의합니다.

사용자가 에디터에서 직접 넣는 문구와, 문구 추천 모델이 보내는 추천안이 같은 형식을 씁니다. 모델·백엔드는 이 형식으로 결과를 보내면 에디터에서 그대로 그려지고, 사용자가 이어서 고칠 수 있습니다.

- FE 타입·검사 함수: `frontend/src/components/editor/textLayer.ts`
- 값 범위 상수: `frontend/src/constants/editor.ts` (`LAYER_LIMITS`)
- 글꼴 목록: `fonts/manifest.json` → `frontend/src/constants/fonts.json` (`scripts/prepare_fonts.py`가 생성)

## 좌표와 크기

위치와 크기는 **픽셀이 아니라 이미지 대비 비율**입니다. 이미지 비율(1:1, 9:16 등)과 해상도, 화면에 보이는 크기와 상관없이 같은 값으로 같은 자리에 그려집니다.

- `x`, `y`: 문구 상자 **가운데**의 위치. 왼쪽 위가 (0, 0), 오른쪽 아래가 (1, 1)
- `width`: 이미지 **가로** 대비 비율
- `fontSize`, 외곽선 두께, 그림자 흐림·거리, 배경 상자 여백: 이미지 **세로** 대비 비율
  - 예) 1024px 높이 이미지에서 `fontSize: 0.08` → 약 82px

## 문구 상자 (TextLayer)

| 필드 | 타입 | 범위 / 값 | 기본값 | 설명 |
|---|---|---|---|---|
| `role` | string \| null | 30자 이하 | `null` | 문구의 역할. 예: `headline`, `subheadline`, `body`, `cta`. 초기 화면의 문구 요청과 짝을 맞출 때 사용 |
| `text` | string | 1~200자, 빈 문구 불가 | (필수) | 표시할 문구. 줄바꿈은 `\n` |
| `x` | number | 0~1 | `0.5` | 상자 가운데 가로 위치 |
| `y` | number | 0~1 | `0.5` | 상자 가운데 세로 위치 |
| `width` | number \| null | 0.05~1 | `null` | 줄바꿈 폭. `null`이면 문구 길이만큼 넓어지고 `\n`에서만 줄을 바꿈 |
| `rotation` | number | -180~180 (도) | `0` | 시계 방향이 + |
| `curve` | number | -100~100 | `0` | 구부리기. 양수는 위로 볼록, 음수는 아래로 볼록, 0은 직선, ±100은 반원. 한 줄 문구에만 적용되며, 구부린 문구는 항상 곡선 가운데에 놓이고 `width`, `align`, `lineHeight`를 쓰지 않음. `\n`이 있으면 값이 있어도 직선으로 그림 |
| `fontId` | string | 글꼴 목록의 `id` | `"pretendard"` | 예: `gmarket-sans`, `black-han-sans`. 모르는 id는 기본 글꼴로 바뀜 |
| `fontSize` | number | 0.01~0.4 | `0.056` | 글자 크기 (이미지 세로 대비) |
| `bold` | boolean | | `false` | 글꼴에 준비된 가장 두꺼운 굵기로 그림 |
| `italic` | boolean | | `false` | |
| `strike` | boolean | | `false` | 취소선 |
| `align` | string | `left` \| `center` \| `right` | `"center"` | 여러 줄일 때 줄 맞춤 |
| `lineHeight` | number | 0.8~2.5 | `1.2` | 줄 간격 (글자 크기 대비) |
| `color` | string | `#RRGGBB` | `"#FFFFFF"` | 글자색 |
| `opacity` | number | 0~1 | `1` | 1이면 불투명. 글자와 배경 상자에 함께 적용 |
| `stroke` | object \| null | 아래 참고 | `null` | 외곽선. 없으면 `null` |
| `shadow` | object \| null | 아래 참고 | `null` | 그림자. 없으면 `null` |
| `background` | object \| null | 아래 참고 | `null` | 글자 뒤 배경 상자. 없으면 `null` |

`id`는 에디터가 붙이므로 보내지 않아도 됩니다(보내도 새로 만듭니다).

### stroke (외곽선)

| 필드 | 타입 | 범위 | 기본값 |
|---|---|---|---|
| `color` | string | `#RRGGBB` | `"#000000"` |
| `width` | number | 0~0.05 (이미지 세로 대비) | `0.004` |
| `opacity` | number | 0~1 | `1` |
| `join` | string | `round`(둥글게) \| `miter`(각지게) | `"round"` |

### shadow (그림자)

| 필드 | 타입 | 범위 | 기본값 |
|---|---|---|---|
| `color` | string | `#RRGGBB` | `"#000000"` |
| `blur` | number | 0~0.1 (이미지 세로 대비) | `0.01` |
| `offsetX` | number | -0.1~0.1 (오른쪽이 +) | `0.003` |
| `offsetY` | number | -0.1~0.1 (아래가 +) | `0.003` |
| `opacity` | number | 0~1 | `0.5` |

### background (배경 상자)

| 필드 | 타입 | 범위 | 기본값 |
|---|---|---|---|
| `color` | string | `#RRGGBB` | `"#000000"` |
| `opacity` | number | 0~1 | `0.5` |
| `padding` | number | 0~0.1 (이미지 세로 대비) | `0.015` |
| `radius` | number | 0~0.1 (이미지 세로 대비) | `0` |

### 예시

```json
{
  "role": "headline",
  "text": "SUMMER SALE",
  "x": 0.5,
  "y": 0.18,
  "width": null,
  "rotation": 0,
  "curve": 0,
  "fontId": "black-han-sans",
  "fontSize": 0.1,
  "bold": false,
  "italic": false,
  "strike": false,
  "align": "center",
  "lineHeight": 1.2,
  "color": "#FFFFFF",
  "opacity": 1,
  "stroke": { "color": "#000000", "width": 0.004, "opacity": 1, "join": "round" },
  "shadow": null,
  "background": null
}
```

## 추천안 (AI 추천안 칩)

모델은 이미지 한 장에 대해 **추천안을 최대 5개** 보냅니다. 추천안 하나는 문구 상자 묶음이며, 에디터 오른쪽의 칩을 누르면 그 묶음이 이미지의 문구로 바뀝니다.

```json
{
  "proposals": [
    {
      "label": "강렬한 헤드라인",
      "layers": [
        { "role": "headline", "text": "SUMMER SALE", "x": 0.5, "y": 0.18, "fontId": "black-han-sans", "fontSize": 0.1, "color": "#FFFFFF" },
        { "role": "body", "text": "전 품목 최대 50%", "x": 0.5, "y": 0.86, "fontId": "pretendard", "fontSize": 0.05, "color": "#FFFFFF" }
      ]
    }
  ]
}
```

- `label`: 칩에 보여줄 짧은 이름
- `layers`: 위 문구 상자 형식의 배열. 뒤에 있을수록 위에 그려짐
- 빠진 필드는 기본값으로 채워지므로 필요한 필드만 보내도 됩니다

## 에디터의 값 검사

모델 결과는 에디터에 들어오기 전에 한곳(`normalizeTextLayer`, `normalizeTextLayers`)에서 검사합니다. 형식이 조금 틀려도 화면이 깨지지 않도록 다음처럼 맞춥니다.

- 범위 밖 숫자 → 범위 안으로 (예: `x: 1.3` → `1`)
- 모르는 `fontId` → 기본 글꼴(`pretendard`)
- 형식이 틀린 색 → 기본값
- 빠진 필드 → 기본값
- `text`가 없거나 빈 문구 → 그 상자는 버림
- 이미지 한 장의 상자가 20개를 넘으면 → 앞에서부터 20개만

## 모델에 알려줄 것

- 글꼴은 `frontend/src/constants/fonts.json`의 `id` 중에서만 고릅니다. 같은 파일의 `category`(signature, headline, body, serif, rounded, handwriting)와 `mood`(느낌)를 고를 때 참고합니다.
- 제품을 가리지 않도록 `x`, `y`, `fontSize`를 정합니다. 상자가 이미지 밖으로 나가지 않게 가운데 위치와 크기를 함께 고려합니다.
- 밝은 배경에는 어두운 글자, 어두운 배경에는 밝은 글자를 쓰고, 배경이 복잡하면 `stroke`, `shadow`, `background`를 씁니다.
