/**
 * 생성 이미지를 크게 보는 팝업 컴포넌트.
 *
 * 생성일자: 2026-11-02
 * 생성자: bioyejin
 * 수정일자: 2026-11-02
 * 수정자: bioyejin
 */

import { useEffect, useRef, type MouseEvent } from "react";
import { createPortal } from "react-dom";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import type { GeneratedImage } from "../../api/client";
import styles from "./ImageViewer.module.css";

export interface ImageViewerProps {
  images: GeneratedImage[];
  /** 크게 보여줄 이미지 순서(0부터). null이면 닫힘 */
  index: number | null;
  /** 이미지 대체 텍스트 (번호는 뒤에 붙인다) */
  alt: string;
  /** [‹] [›] 버튼이나 ←/→ 키로 다른 이미지를 고를 때 호출 */
  onIndexChange: (index: number) => void;
  /** [✕] 버튼, Esc 키, 바깥 영역 클릭 시 호출 */
  onClose: () => void;
}

/**
 * 고른 이미지를 어두운 반투명 레이어 위에 크게 띄운다. 좌우 버튼과 ←/→ 키로 넘기고
 * (끝에서는 처음으로 돌아감), 이미지 아래 가운데에 순서, 오른쪽 구석에 seed를 작게 표시한다.
 *
 * @param props - 이미지 목록, 보여줄 순서, 대체 텍스트, 넘기기·닫기 처리 함수
 * @returns 열려 있으면 화면 위에 뜨는 레이어, 닫혀 있으면 null
 */
export default function ImageViewer({
  images,
  index,
  alt,
  onIndexChange,
  onClose,
}: ImageViewerProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const open = index !== null;
  const count = images.length;

  // 열릴 때 닫기 버튼에 포커스
  useEffect(() => {
    if (open) closeRef.current?.focus();
  }, [open]);

  // 열려 있는 동안 Esc로 닫고 ←/→로 넘긴다
  useEffect(() => {
    if (index === null) return;
    const current = index;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft") onIndexChange((current - 1 + count) % count);
      else if (e.key === "ArrowRight") onIndexChange((current + 1) % count);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [index, count, onIndexChange, onClose]);

  if (index === null) return null;
  const image = images[index];
  if (!image) return null;

  /**
   * 레이어 위 버튼을 눌렀을 때 바깥 영역 클릭(닫기)으로 처리되지 않게 하고 동작을 실행한다.
   *
   * @param action - 실행할 동작
   * @returns 버튼 클릭 처리 함수
   */
  function onButtonClick(action: () => void) {
    return (e: MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      action();
    };
  }

  // 바깥 레이어를 누르면 닫고, 이미지 위를 누르면 닫지 않는다
  return createPortal(
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-label="이미지 크게 보기"
      onClick={onClose}
    >
      <figure className={styles.figure} onClick={(e) => e.stopPropagation()}>
        {/* 좌우 버튼은 이미지 기준으로 위치를 잡아, 화면 끝과 이미지 사이 가운데에 둔다 */}
        <div className={styles.imageWrap}>
          <img
            className={styles.image}
            src={`data:image/png;base64,${image.image_base64}`}
            alt={`${alt} (${index + 1}/${count})`}
          />
          {count > 1 && (
            <>
              <button
                type="button"
                className={`${styles.iconButton} ${styles.prev}`}
                aria-label="이전 이미지"
                onClick={onButtonClick(() => onIndexChange((index - 1 + count) % count))}
              >
                <ChevronLeft size={32} />
              </button>
              <button
                type="button"
                className={`${styles.iconButton} ${styles.next}`}
                aria-label="다음 이미지"
                onClick={onButtonClick(() => onIndexChange((index + 1) % count))}
              >
                <ChevronRight size={32} />
              </button>
            </>
          )}
        </div>
        <figcaption className={styles.caption}>
          <span className={styles.counter}>
            {index + 1} / {count}
          </span>
          <span className={styles.seed}>seed {image.seed}</span>
        </figcaption>
      </figure>

      <button
        ref={closeRef}
        type="button"
        className={`${styles.iconButton} ${styles.close}`}
        aria-label="닫기"
        onClick={onButtonClick(onClose)}
      >
        <X size={24} />
      </button>
    </div>,
    document.body,
  );
}
