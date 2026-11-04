/**
 * 에디터 상단의 썸네일 줄 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

import type { GeneratedImage } from "../../api/client";
import styles from "./ThumbnailStrip.module.css";

export interface ThumbnailStripProps {
  images: GeneratedImage[];
  /** 지금 편집 중인 이미지 순서(0부터) */
  selectedIndex: number;
  /** 서버 해상도. 이미지를 읽기 전에도 썸네일 비율을 잡는 데 쓴다 */
  width: number;
  height: number;
  /** 썸네일을 눌러 다른 이미지를 고를 때 호출 */
  onSelect: (index: number) => void;
}

/**
 * 생성된 이미지를 작게 한 줄로 보여주고, 누르면 그 이미지를 편집하도록 고른다.
 * 지금 편집 중인 이미지는 테두리로 표시한다.
 *
 * @param props - 이미지 목록, 고른 순서, 해상도, 고르기 처리 함수
 * @returns 썸네일 줄
 */
export default function ThumbnailStrip({
  images,
  selectedIndex,
  width,
  height,
  onSelect,
}: ThumbnailStripProps) {
  return (
    <div className={styles.strip} role="group" aria-label="편집할 이미지 고르기">
      {images.map((image, index) => {
        const selected = index === selectedIndex;
        return (
          <button
            key={`${index}-${image.seed}`}
            type="button"
            className={`${styles.thumb} ${selected ? styles.selected : ""}`}
            aria-label={`${index + 1}번째 이미지 편집`}
            aria-pressed={selected}
            onClick={() => onSelect(index)}
          >
            <img
              className={styles.image}
              src={`data:image/png;base64,${image.image_base64}`}
              alt=""
              width={width}
              height={height}
            />
          </button>
        );
      })}
    </div>
  );
}
