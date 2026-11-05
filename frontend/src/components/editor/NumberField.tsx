/**
 * 숫자 입력 칸 컴포넌트.
 *
 * 생성일자: 2026-11-05
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
 * 수정자: bioyejin
 */

import { useEffect, useState } from "react";
import { Minus, Plus } from "lucide-react";
import styles from "./NumberField.module.css";

export interface NumberFieldProps {
  /** 지금 값 */
  value: number;
  min: number;
  max: number;
  /** 값을 맞출 단위 (기본 1) */
  step?: number;
  /** 주면 칸 양옆에 이 값만큼 바꾸는 [−] [+] 버튼을 둔다 */
  buttonStep?: number;
  /** [−] [+] 버튼 이름에 쓴다 (예: 크기 → "크기 줄이기") */
  label?: string;
  id?: string;
  /** 입력을 마쳤을 때 범위 안으로 맞춘 값을 알린다 */
  onChange: (value: number) => void;
}

/**
 * 값을 단위에 맞추고 범위 안으로 맞춘다.
 *
 * @param value - 값
 * @param step - 단위
 * @param min - 최솟값
 * @param max - 최댓값
 * @returns 맞춘 값
 */
function fitValue(value: number, step: number, min: number, max: number): number {
  // 0.1 단위 계산에서 생기는 소수 오차(1.3000000000000003)를 없앤다
  const rounded = Number((Math.round(value / step) * step).toFixed(2));
  return Math.min(max, Math.max(min, rounded));
}

/**
 * 숫자 입력 칸. 입력하는 도중(예: "56"을 치려고 "5"만 친 상태)에 범위로 바뀌지 않도록
 * 칸 밖으로 나가거나 Enter를 누를 때 반영한다.
 *
 * @param props - 지금 값, 범위, 단위, 버튼 단위, 변경 처리 함수
 * @returns 숫자 입력 칸
 */
export default function NumberField({
  value,
  min,
  max,
  step = 1,
  buttonStep,
  label,
  id,
  onChange,
}: NumberFieldProps) {
  const [draft, setDraft] = useState(String(value));

  // 슬라이더나 캔버스 조작으로 값이 바뀌면 따라간다
  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  /** 입력한 값을 반영한다. 숫자가 아니면 원래 값으로 되돌린다. */
  function commit() {
    const parsed = Number(draft);
    if (draft.trim() === "" || !Number.isFinite(parsed)) {
      setDraft(String(value));
      return;
    }
    const next = fitValue(parsed, step, min, max);
    setDraft(String(next));
    if (next !== value) onChange(next);
  }

  const input = (
    <input
      id={id}
      type="number"
      className={styles.number}
      min={min}
      max={max}
      step={step}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
      }}
    />
  );

  if (buttonStep === undefined) return input;

  return (
    <span className={styles.stepper}>
      <button
        type="button"
        className={styles.stepButton}
        aria-label={`${label} 줄이기`}
        disabled={value <= min}
        onClick={() => onChange(fitValue(value - buttonStep, step, min, max))}
      >
        <Minus size={12} />
      </button>
      {input}
      <button
        type="button"
        className={styles.stepButton}
        aria-label={`${label} 키우기`}
        disabled={value >= max}
        onClick={() => onChange(fitValue(value + buttonStep, step, min, max))}
      >
        <Plus size={12} />
      </button>
    </span>
  );
}
