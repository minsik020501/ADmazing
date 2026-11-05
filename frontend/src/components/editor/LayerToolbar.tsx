/**
 * 선택한 문구 상자 위에 뜨는 작은 도구줄 컴포넌트.
 *
 * 생성일자: 2026-11-05
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
 * 수정자: bioyejin
 */

import { Copy, Trash2, Type } from "lucide-react";
import styles from "./LayerToolbar.module.css";

/** 도구줄 크기(px). 캔버스 밖으로 나가지 않게 위치를 맞추는 데 쓴다 */
export const LAYER_TOOLBAR_WIDTH = 92;
export const LAYER_TOOLBAR_HEIGHT = 32;

export interface LayerToolbarProps {
  /** 도구줄 왼쪽 위 위치 (캔버스 기준 화면 px) */
  left: number;
  top: number;
  onEdit: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}

/**
 * [문구 고치기] [복제] [삭제] 버튼을 보여준다.
 *
 * @param props - 위치와 버튼 처리 함수
 * @returns 도구줄
 */
export default function LayerToolbar({
  left,
  top,
  onEdit,
  onDuplicate,
  onDelete,
}: LayerToolbarProps) {
  return (
    <div
      className={styles.toolbar}
      style={{ left, top }}
      role="toolbar"
      aria-label="문구 상자 도구"
    >
      <button
        type="button"
        className={styles.button}
        aria-label="문구 고치기"
        title="문구 고치기"
        onClick={onEdit}
      >
        <Type size={13} />
      </button>
      <button
        type="button"
        className={styles.button}
        aria-label="상자 복제"
        title="상자 복제"
        onClick={onDuplicate}
      >
        <Copy size={13} />
      </button>
      <button
        type="button"
        className={styles.button}
        aria-label="상자 삭제"
        title="상자 삭제"
        onClick={onDelete}
      >
        <Trash2 size={13} />
      </button>
    </div>
  );
}
