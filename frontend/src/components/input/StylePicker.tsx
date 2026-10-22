/**
 * 이미지 스타일 선택 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import { useId } from "react";
import { STYLE_PRESETS } from "../../constants/stylePresets";
import Chip from "../common/Chip";
import SectionLabel from "../common/SectionLabel";
import styles from "./StylePicker.module.css";

export interface StylePickerProps {
  /** 선택된 스타일 id */
  value: string;
  onChange: (styleId: string) => void;
}

/**
 * "3. 스타일" 섹션. 스타일 칩 중 하나만 고를 수 있다.
 *
 * @param props - 선택된 스타일 id와 변경 처리 함수
 * @returns 스타일 선택 섹션
 */
export default function StylePicker({ value, onChange }: StylePickerProps) {
  const labelId = useId();

  return (
    <section className={styles.section} aria-labelledby={labelId}>
      <SectionLabel
        id={labelId}
        number={3}
        title="스타일"
        description="이미지의 전체적인 표현 방식을 골라 주세요"
      />
      <div className={styles.chips}>
        {STYLE_PRESETS.map((preset) => (
          <Chip key={preset.id} selected={preset.id === value} onClick={() => onChange(preset.id)}>
            {preset.label}
          </Chip>
        ))}
      </div>
    </section>
  );
}
