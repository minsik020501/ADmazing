/**
 * 슬라이더와 숫자 입력 칸을 묶은 값 조절 컴포넌트.
 *
 * 생성일자: 2026-11-05
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { useId } from "react";
import NumberField from "./NumberField";
import styles from "./SliderField.module.css";

export interface SliderFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  /** 숫자 뒤에 붙이는 단위 (예: px, °) */
  unit?: string;
  /**
   * 슬라이더를 0에서 이 값 안쪽으로 옮기면 0에 붙인다 (회전·구부리기를 정확히 0으로 되돌리기 쉽게).
   * 숫자 칸에 직접 입력한 값은 그대로 둔다. 없으면 붙이지 않는다
   */
  snapToZero?: number;
  onChange: (value: number) => void;
}

/**
 * 왼쪽에 이름, 오른쪽에 슬라이더와 숫자 입력 칸을 한 줄로 보여준다.
 *
 * @param props - 이름, 값, 범위, 단위, 0 맞춤 범위, 변경 처리 함수
 * @returns 값 조절 묶음
 */
export default function SliderField({
  label,
  value,
  min,
  max,
  unit,
  snapToZero,
  onChange,
}: SliderFieldProps) {
  const id = useId();

  /**
   * 슬라이더 값을 받아, 0 가까이면 0으로 맞춰 넘긴다.
   *
   * @param next - 슬라이더 값
   */
  function handleSlide(next: number) {
    onChange(snapToZero !== undefined && Math.abs(next) <= snapToZero ? 0 : next);
  }

  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label}
      </label>
      <input
        type="range"
        className={styles.range}
        min={min}
        max={max}
        value={value}
        aria-label={`${label} 조절`}
        onChange={(e) => handleSlide(Number(e.target.value))}
      />
      <NumberField id={id} value={value} min={min} max={max} onChange={onChange} />
      <span className={styles.unit}>{unit}</span>
    </div>
  );
}
