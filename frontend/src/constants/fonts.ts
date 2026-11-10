/**
 * 광고 문구용 폰트 목록.
 *
 * 목록은 fonts.json에서 읽는다. fonts.json과 styles/fonts.css(@font-face)는
 * scripts/prepare_fonts.py가 fonts/manifest.json으로 만들므로, 폰트를 바꿀 때는 manifest를 고친다.
 * 폰트 파일은 docker compose의 font-prep이 준비해 /fonts/... 경로로 제공한다.
 *
 * 생성일자: 2026-11-04
 * 생성자: ven_choi
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import fontList from "./fonts.json";

/** 폰트 분류 */
export type AdFontCategory =
  | "signature"
  | "headline"
  | "body"
  | "serif"
  | "rounded"
  | "handwriting";

/** 광고 문구에 쓸 수 있는 폰트 하나 */
export interface AdFont {
  id: string;
  /** 화면에 표시할 이름 */
  name: string;
  /** CSS font-family 값 (styles/fonts.css의 @font-face와 같음) */
  family: string;
  category: AdFontCategory;
  /** 폰트 느낌 (추천 이유·설명에 사용) */
  mood: string;
  /** 준비된 굵기 (CSS font-weight 값, 오름차순) */
  weights: number[];
  license: string;
  /** 라이선스를 확인할 수 있는 페이지 */
  licenseUrl: string;
}

/** 분류별 화면 표시 이름 (화면에 보여 줄 순서) */
export const FONT_CATEGORY_LABELS: Record<AdFontCategory, string> = {
  signature: "시그니처",
  headline: "임팩트 헤드라인",
  body: "본문 · 서브카피",
  serif: "고급 · 감성 명조",
  rounded: "부드러운 둥근 고딕",
  handwriting: "손글씨 · 캘리그라피",
};

/** 광고 문구용 폰트 전체 (manifest 순서) */
export const AD_FONTS = fontList.fonts as AdFont[];

/**
 * CSS font-family 값을 만든다. 폰트 파일을 못 받았을 때를 위해 기본 글꼴을 뒤에 붙인다.
 *
 * @param font - 사용할 폰트
 * @returns CSS font-family 값 (예: `"Pretendard", sans-serif`)
 */
export function toFontFamily(font: AdFont): string {
  const fallback = font.category === "serif" ? "serif" : "sans-serif";
  return `"${font.family}", ${fallback}`;
}
