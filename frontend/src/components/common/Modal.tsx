/**
 * 공통 확인 팝업(모달) 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import Button from "./Button";
import styles from "./Modal.module.css";

export interface ModalProps {
  open: boolean;
  title: string;
  /** 제목 아래 설명 내용 */
  children?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  /** 취소 버튼, Esc 키, 바깥 영역 클릭 시 호출 */
  onCancel: () => void;
}

/**
 * 확인/취소를 묻는 팝업. 열리면 확인 버튼에 포커스가 가서 Enter로 바로 확인할 수 있다.
 *
 * @param props - 열림 여부, 제목, 설명, 버튼 문구와 확인/취소 처리
 * @returns 열려 있으면 화면 위에 뜨는 팝업, 닫혀 있으면 null
 */
export default function Modal({
  open,
  title,
  children,
  confirmLabel = "확인",
  cancelLabel = "취소",
  onConfirm,
  onCancel,
}: ModalProps) {
  const titleId = useId();
  const confirmRef = useRef<HTMLButtonElement>(null);

  // 열릴 때 확인 버튼에 포커스
  useEffect(() => {
    if (open) confirmRef.current?.focus();
  }, [open]);

  // 열려 있는 동안 Esc 키로 취소
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  // 화면 맨 위에 그려지도록 body 바로 아래에 붙인다
  return createPortal(
    <div className={styles.backdrop} onClick={onCancel}>
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className={styles.title}>
          {title}
        </h2>
        {children && <div className={styles.body}>{children}</div>}
        <div className={styles.actions}>
          <Button variant="secondary" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button ref={confirmRef} variant="primary" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
