/**
 * 공통 칩(선택형 작은 버튼) 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import type { ReactNode } from "react";
import styles from "./Chip.module.css";

export interface ChipProps {
  /** 선택된 상태인지 여부. 예시 칩처럼 선택 상태가 없으면 생략 */
  selected?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children: ReactNode;
}

/**
 * 예시 프롬프트, 스타일·비율 선택 등에 함께 쓰는 작은 버튼.
 * selected를 넘기면 선택된 칩을 포인트 색으로 표시한다.
 *
 * @param props - 선택 상태, 비활성 여부, 클릭 처리, 표시 내용
 * @returns 칩 버튼 요소
 */
export default function Chip({ selected, disabled, onClick, children }: ChipProps) {
  const classes = [styles.chip, selected && styles.selected].filter(Boolean).join(" ");

  return (
    <button
      type="button"
      className={classes}
      aria-pressed={selected}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
