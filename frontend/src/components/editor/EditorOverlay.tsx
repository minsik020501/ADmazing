/**
 * 에디터의 미리보기·저장 화면에 쓰는 어두운 레이어 컴포넌트.
 *
 * 생성일자: 2026-11-05
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
 * 수정자: bioyejin
 */

import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import styles from "./EditorOverlay.module.css";

export interface EditorOverlayProps {
  /** 화면 낭독기가 읽는 이름 */
  label: string;
  children: ReactNode;
  /** [✕] 버튼, Esc 키, 바깥 영역 클릭 시 호출 */
  onClose: () => void;
}

/**
 * 어두운 반투명 레이어 위 화면 가운데에 내용을 띄운다.
 *
 * @param props - 이름, 가운데에 띄울 내용, 닫기 처리 함수
 * @returns 화면 위에 뜨는 레이어
 */
export default function EditorOverlay({ label, children, onClose }: EditorOverlayProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return createPortal(
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-label={label}
      onClick={onClose}
    >
      <div className={styles.content} onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
      <button
        ref={closeRef}
        type="button"
        className={styles.close}
        aria-label="닫기"
        onClick={onClose}
      >
        <X size={24} />
      </button>
    </div>,
    document.body,
  );
}
