/**
 * AI 추천안의 레이아웃·글꼴 스타일 목록. id는 백엔드 배치 추천(/api/layout/recommend)과 같다.
 *
 * 생성일자: 2026-11-10
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

/** 화면에서 고를 수 있는 항목 하나 */
export interface LayoutOption {
  id: string;
  label: string;
}

/** 레이아웃 (화면에 보여 줄 순서) */
export const LAYOUT_TEMPLATES: LayoutOption[] = [
  { id: "top_left", label: "좌상단" },
  { id: "top_right", label: "우상단" },
  { id: "top_center", label: "중앙상단" },
  { id: "bottom_center", label: "중앙하단" },
  { id: "bottom_left", label: "좌하단" },
  { id: "bottom_right", label: "우하단" },
  { id: "side_left", label: "좌패널" },
  { id: "side_right", label: "우패널" },
];

/**
 * 글꼴 스타일 (화면에 보여 줄 순서). 제목 글꼴 + 본문 글꼴 조합이며, 굵게는 Title에만 쓴다.
 * 칩에 들어가도록 이름을 2~4글자로 줄였다 (주석은 원래 이름과 글꼴)
 */
export const FONT_STYLES: LayoutOption[] = [
  // 미니멀·모던 고딕: G마켓 산스 + 나눔스퀘어
  { id: "minimal_gothic", label: "모던" },
  // 세리프 감성: 부크크 명조
  { id: "serif", label: "명조" },
  // 깔끔한 느낌: 페이퍼로지 + 프리텐다드
  { id: "clean", label: "깔끔" },
  // 시그니처: Mona12 (화면 UI와 같은 픽셀 글꼴)
  { id: "signature", label: "시그니처" },
  // 손글씨 느낌: 잉크립퀴드체 + 나눔손글씨 붓
  { id: "handwriting", label: "손글씨" },
  // 임팩트 세일: 빗썸고딕 + 페이퍼로지
  { id: "impact_sale", label: "파격" },
  // 부드러운 둥근 느낌: 학교안심 둥근미소
  { id: "rounded", label: "둥근" },
];

/** 폭이 좁은 패널 레이아웃. 아래 비율에서는 긴 문구가 넘칠 수 있다 */
export const NARROW_PANEL_TEMPLATES = ["side_left", "side_right"];

/** 패널 레이아웃의 폭이 좁아지는 비율 (정사각형·가로형) */
export const NARROW_PANEL_RATIOS = ["1:1", "4:3", "3:2", "16:9"];

/** 좁은 패널 조합을 골랐을 때 안내 */
export const NARROW_PANEL_MESSAGE = "패널 폭이 좁아 긴 문구가 넘칠 수 있어요";

/**
 * 레이아웃과 이미지 비율이 폭이 좁은 패널 조합인지 확인한다.
 *
 * @param templateId - 레이아웃 id
 * @param ratio - 이미지 비율 (예: "16:9")
 * @returns 좁은 패널 조합이면 true
 */
export function isNarrowPanel(templateId: string, ratio: string): boolean {
  return NARROW_PANEL_TEMPLATES.includes(templateId) && NARROW_PANEL_RATIOS.includes(ratio);
}

/** 추천안 칩에 보여줄 Title 글자 수. 넘으면 뒤를 …으로 줄인다 */
export const CHIP_TITLE_LENGTH = 10;

/** AI가 스타일을 고르지 못했을 때 쓰는 스타일 */
export const FALLBACK_STYLE_ID = FONT_STYLES[0].id;

/**
 * AI가 고른 스타일 중 화면 목록에 있는 첫 번째 스타일을 찾는다.
 *
 * @param styles - 문구 추천 결과의 스타일 id (어울리는 순서)
 * @returns 추천 스타일 id. 쓸 수 있는 스타일이 없으면 null
 */
export function pickRecommendedStyle(styles: string[]): string | null {
  return styles.find((id) => FONT_STYLES.some((option) => option.id === id)) ?? null;
}
