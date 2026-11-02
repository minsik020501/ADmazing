/**
 * 이미지 스타일 목록.
 *
 * 서버에 스타일 항목이 없어서, 고른 스타일의 문구를 프롬프트 뒤에 붙여 보낸다.
 * 서버가 프롬프트를 영어로 번역할 때 이 문구도 함께 번역된다.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

/** 이미지 스타일 하나 */
export interface StylePreset {
  id: string;
  /** 칩에 표시할 이름 */
  label: string;
  /** 프롬프트 뒤에 붙일 문구. 빈 문자열이면 붙이지 않는다 */
  suffix: string;
}

export const DEFAULT_STYLE_ID = "none";

export const STYLE_PRESETS: StylePreset[] = [
  { id: DEFAULT_STYLE_ID, label: "없음", suffix: "" },
  { id: "photo", label: "실사 사진", suffix: "실사 사진 스타일, 사실적인 디테일" },
  { id: "studio", label: "제품 스튜디오", suffix: "제품 스튜디오 촬영, 깔끔한 배경과 조명" },
  { id: "illustration", label: "일러스트", suffix: "일러스트 스타일" },
  { id: "3d", label: "3D 렌더", suffix: "3D 렌더링 스타일" },
  { id: "minimal", label: "미니멀", suffix: "미니멀한 스타일, 여백이 많은 구성" },
  { id: "vintage", label: "빈티지", suffix: "빈티지 필름 사진 느낌" },
];
