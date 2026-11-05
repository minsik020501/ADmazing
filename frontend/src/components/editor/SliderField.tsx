/**
 * 슬라이더와 숫자 입력 칸을 묶은 값 조절 컴포넌트.
 *
 * 생성일자: 2026-11-05
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
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
  onChange: (value: number) => void;
}

/**
 * 왼쪽에 이름, 오른쪽에 슬라이더와 숫자 입력 칸을 한 줄로 보여준다.
 *
 * @param props - 이름, 값, 범위, 단위, 변경 처리 함수
 * @returns 값 조절 묶음
 */
export default function SliderField({ label, value, min, max, unit, onChange }: SliderFieldProps) {
  const id = useId();

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
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <NumberField id={id} value={value} min={min} max={max} onChange={onChange} />
      <span className={styles.unit}>{unit}</span>
    </div>
  );
}
