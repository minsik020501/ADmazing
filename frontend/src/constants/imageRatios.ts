/**
 * 이미지 비율 목록.
 *
 * value는 서버가 허용하는 ratio 값과 같아야 한다 (backend/fastapi/app/core/image_ratio.py).
 * 해상도는 서버가 비율에 맞춰 정하므로 프론트엔드는 비율만 보낸다.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

/** 이미지 비율 하나 */
export interface ImageRatio {
  /** 서버로 보내는 비율 값 (가로:세로) */
  value: string;
  /** 칩에 표시할 용도·채널 이름 */
  label: string;
  /** 비율 모양 아이콘을 그릴 때 쓰는 가로·세로 비 */
  width: number;
  height: number;
}

export const DEFAULT_RATIO = "1:1";

/** 화면에는 4개씩 2줄로 보인다. 윗줄은 정사각형·세로형, 아랫줄은 세로 긴 형·가로형 */
export const IMAGE_RATIOS: ImageRatio[] = [
  { value: "1:1", label: "정사각형", width: 1, height: 1 },
  { value: "4:5", label: "세로 피드", width: 4, height: 5 },
  { value: "3:4", label: "세로", width: 3, height: 4 },
  { value: "2:3", label: "포스터", width: 2, height: 3 },
  { value: "9:16", label: "스토리·릴스", width: 9, height: 16 },
  { value: "16:9", label: "배너·유튜브", width: 16, height: 9 },
  { value: "4:3", label: "가로", width: 4, height: 3 },
  { value: "3:2", label: "사진", width: 3, height: 2 },
];
