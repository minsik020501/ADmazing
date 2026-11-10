/**
 * 레이아웃 위치 아이콘 컴포넌트.
 *
 * 생성일자: 2026-11-10
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

/** 아이콘 안의 글자 막대 하나 (x, y, 폭) */
type Bar = [x: number, y: number, width: number];

// 24×24 칸 안에 이미지 틀(2~22 × 4~20)을 그리고, 문구 자리를 막대로 표시한다.
// 블록형은 긴 막대(제목) + 짧은 막대(본문), 패널형은 좁은 세로 칸에 짧은 막대 3개
const BARS: Record<string, Bar[]> = {
  top_left: [
    [5, 7, 8],
    [5, 10.5, 5],
  ],
  top_right: [
    [11, 7, 8],
    [14, 10.5, 5],
  ],
  top_center: [
    [8, 7, 8],
    [9.5, 10.5, 5],
  ],
  bottom_center: [
    [8, 12.5, 8],
    [9.5, 16, 5],
  ],
  bottom_left: [
    [5, 12.5, 8],
    [5, 16, 5],
  ],
  bottom_right: [
    [11, 12.5, 8],
    [14, 16, 5],
  ],
  side_left: [
    [5, 8, 5],
    [5, 11, 5],
    [5, 14, 5],
  ],
  side_right: [
    [14, 8, 5],
    [14, 11, 5],
    [14, 14, 5],
  ],
};

/** 막대 두께 */
const BAR_HEIGHT = 2;

export interface LayoutIconProps {
  /** 레이아웃 id (constants/layoutOptions.ts) */
  templateId: string;
  /** 아이콘 크기(px) */
  size?: number;
}

/**
 * 이미지 틀 안에 문구 블록이 놓이는 자리를 막대로 그린 아이콘. 색은 글자색(currentColor)을 따른다.
 *
 * @param props - 레이아웃 id, 크기
 * @returns SVG 아이콘
 */
export default function LayoutIcon({ templateId, size = 24 }: LayoutIconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
      <rect
        x={2.5}
        y={4.5}
        width={19}
        height={15}
        rx={2}
        fill="none"
        stroke="currentColor"
        strokeOpacity={0.5}
      />
      {(BARS[templateId] ?? []).map(([x, y, width]) => (
        <rect
          key={`${x}-${y}`}
          x={x}
          y={y}
          width={width}
          height={BAR_HEIGHT}
          rx={1}
          fill="currentColor"
        />
      ))}
    </svg>
  );
}
