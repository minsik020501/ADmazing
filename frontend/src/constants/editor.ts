/**
 * 텍스트 에디터 화면에서 쓰는 상수.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-06
 * 수정자: bioyejin
 */

/** 내려받는 이미지 파일 이름의 앞부분. 예: admazing_seed42.png */
export const IMAGE_FILE_PREFIX = "admazing";

/** 편집본 파일 이름 끝에 붙이는 표시. 예: admazing_seed42_edited.png */
export const EDITED_FILE_SUFFIX = "edited";

/** 새 문구 상자에 미리 들어가는 문구 (추가하면 선택된 채로 입력 상태가 되어 바로 덮어쓴다) */
export const DEFAULT_LAYER_TEXT = "텍스트를 입력하세요";

/** 새 문구 상자와, 모르는 글꼴 id가 들어왔을 때 쓰는 글꼴 (constants/fonts.ts의 id) */
export const DEFAULT_FONT_ID = "pretendard";

/** 새 문구 상자의 글자 크기 (이미지 세로 대비 비율) */
export const DEFAULT_FONT_SIZE = 0.056;

/** 문구 상자 값의 허용 범위. 화면 조작과 모델 결과 검사에 같이 쓴다 */
export const LAYER_LIMITS = {
  /** 글자 크기 (이미지 세로 대비 비율) */
  fontSize: { min: 0.01, max: 0.4 },
  /** 줄바꿈 폭 (이미지 가로 대비 비율). null이면 Enter로만 줄을 바꾼다 */
  width: { min: 0.05, max: 1 },
  /** 회전 (도) */
  rotation: { min: -180, max: 180 },
  /** 구부리기 (-100: 아래로 볼록, 100: 위로 볼록) */
  curve: { min: -100, max: 100 },
  /** 외곽선 두께 (이미지 세로 대비 비율) */
  strokeWidth: { min: 0, max: 0.05 },
  /** 그림자 흐림·거리 (이미지 세로 대비 비율) */
  shadowBlur: { min: 0, max: 0.1 },
  shadowOffset: { min: -0.1, max: 0.1 },
  /** 줄 간격 (글자 크기 대비) */
  lineHeight: { min: 0.8, max: 2.5 },
  /** 배경 상자 여백 (이미지 세로 대비 비율) */
  backgroundPadding: { min: 0, max: 0.1 },
  /** 배경 상자 모서리 둥글기 (이미지 세로 대비 비율) */
  backgroundRadius: { min: 0, max: 0.1 },
  /** 문구 길이 */
  textLength: { max: 200 },
  /** 이미지 한 장의 문구 상자 개수 */
  layerCount: { max: 20 },
} as const;

/** 글자색 빠른 선택 (그 밖의 색은 색상 선택기로 고른다) */
export const TEXT_COLOR_PRESETS = [
  { value: "#FFFFFF", label: "흰색" },
  { value: "#000000", label: "검정" },
  { value: "#E53935", label: "빨강" },
  { value: "#FB8C00", label: "주황" },
  { value: "#FDD835", label: "노랑" },
  { value: "#43A047", label: "초록" },
  { value: "#1E88E5", label: "파랑" },
  { value: "#8E24AA", label: "보라" },
] as const;

/** 효과 슬라이더의 최댓값 (원본 이미지 px) */
export const EFFECT_MAX_PX = {
  strokeWidth: 40,
  shadowDistance: 30,
  shadowBlur: 50,
  backgroundPadding: 50,
} as const;

/** 크기 [−] [+] 버튼을 한 번 누를 때 바뀌는 글자 크기 (원본 이미지 px) */
export const FONT_SIZE_BUTTON_STEP_PX = 2;

/** 줄 간격 [−] [+] 버튼을 한 번 누를 때 바뀌는 값 */
export const LINE_HEIGHT_BUTTON_STEP = 0.1;

/** 새 문구 상자의 줄 간격 (글자 크기 대비) */
export const DEFAULT_LINE_HEIGHT = 1.2;

/** 외곽선을 켤 때와, 모델 결과에 값이 빠졌을 때 쓰는 기본값 */
export const DEFAULT_STROKE = {
  color: "#000000",
  width: 0.004,
  opacity: 1,
  join: "round",
} as const;

/** 그림자를 켤 때와, 모델 결과에 값이 빠졌을 때 쓰는 기본값 */
export const DEFAULT_SHADOW = {
  color: "#000000",
  blur: 0.01,
  offsetX: 0.003,
  offsetY: 0.003,
  opacity: 0.5,
} as const;

/** 배경 상자를 켤 때와, 모델 결과에 값이 빠졌을 때 쓰는 기본값 */
export const DEFAULT_BACKGROUND = {
  color: "#000000",
  opacity: 0.5,
  padding: 0.015,
  radius: 0,
} as const;

/** 편집 영역의 최대 높이 (화면 높이 대비 비율) */
export const STAGE_MAX_HEIGHT_RATIO = 0.7;

/** 확대·축소 범위와 한 번에 바뀌는 양 (원본 대비 배율) */
export const ZOOM_LIMITS = { min: 0.25, max: 2, step: 0.25 } as const;

/** 휠을 굴린 양(px)을 배율 변화로 바꾸는 값. 클수록 빠르게 확대·축소된다 */
export const ZOOM_WHEEL_SPEED = 0.0015;

/** 복제한 문구 상자를 원본에서 비켜 놓는 거리 (이미지 대비 비율) */
export const DUPLICATE_OFFSET = 0.03;

/** 선택 테두리가 문구 상자에서 떨어진 거리 (화면 px) */
export const SELECTION_PADDING_PX = 6;

/** 이미지 한 장에서 되돌릴 수 있는 최대 단계 */
export const HISTORY_LIMIT = 50;

/** 같은 항목을 이 시간(ms) 안에 이어서 바꾸면 되돌리기 한 단계로 묶는다 (슬라이더 끌기 등) */
export const HISTORY_GROUP_MS = 500;
