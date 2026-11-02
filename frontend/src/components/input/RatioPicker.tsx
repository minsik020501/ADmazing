/**
 * 이미지 비율 선택 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import { useId, type CSSProperties } from "react";
import { IMAGE_RATIOS, type ImageRatio } from "../../constants/imageRatios";
import Chip from "../common/Chip";
import SectionLabel from "../common/SectionLabel";
import styles from "./RatioPicker.module.css";

/** 비율 모양 아이콘의 긴 변 길이(px) */
const ICON_SIZE = 14;

/**
 * 비율에 맞는 아이콘 크기를 구한다. 긴 변을 ICON_SIZE로 맞추고 짧은 변은 비율대로 줄인다.
 *
 * @param ratio - 비율
 * @returns 아이콘의 width, height 스타일
 */
function iconStyle(ratio: ImageRatio): CSSProperties {
  const longer = Math.max(ratio.width, ratio.height);
  return {
    width: Math.round((ICON_SIZE * ratio.width) / longer),
    height: Math.round((ICON_SIZE * ratio.height) / longer),
  };
}

export interface RatioPickerProps {
  /** 선택된 비율 값 (예: "16:9") */
  value: string;
  onChange: (ratio: string) => void;
}

/**
 * "4. 비율" 섹션. 비율 모양 아이콘, 비율, 용도 이름이 담긴 칩 중 하나를 고른다.
 *
 * @param props - 선택된 비율과 변경 처리 함수
 * @returns 비율 선택 섹션
 */
export default function RatioPicker({ value, onChange }: RatioPickerProps) {
  const labelId = useId();

  return (
    <section className={styles.section} aria-labelledby={labelId}>
      <SectionLabel
        id={labelId}
        number={4}
        title="비율"
        description="광고를 올릴 곳에 맞는 가로:세로 비율을 골라 주세요"
      />
      <div className={styles.grid}>
        {IMAGE_RATIOS.map((ratio) => (
          <Chip
            key={ratio.value}
            selected={ratio.value === value}
            onClick={() => onChange(ratio.value)}
          >
            <span className={styles.iconBox} aria-hidden>
              <span className={styles.icon} style={iconStyle(ratio)} />
            </span>
            <span className={styles.ratio}>{ratio.value}</span>
            <span className={styles.name}>{ratio.label}</span>
          </Chip>
        ))}
      </div>
    </section>
  );
}
