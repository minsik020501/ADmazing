/**
 * 에디터 오른쪽의 탭 패널 컴포넌트.
 *
 * 생성일자: 2026-11-05
 * 생성자: bioyejin
 * 수정일자: 2026-11-11
 * 수정자: bioyejin
 */

import { useId, type ReactNode } from "react";
import styles from "./EditorSidePanel.module.css";

export type PanelTab = "ai" | "text";

const TABS: { id: PanelTab; label: string }[] = [
  { id: "ai", label: "AI 추천" },
  { id: "text", label: "텍스트 편집기" },
];

export interface EditorSidePanelProps {
  /** 지금 보이는 탭 */
  tab: PanelTab;
  /** 탭 버튼을 누를 때 호출 */
  onTabChange: (tab: PanelTab) => void;
  /** [AI 추천] 탭 내용 */
  ai: ReactNode;
  /** [텍스트 편집기] 탭 내용 */
  children: ReactNode;
}

/**
 * [AI 추천], [텍스트 편집기] 탭을 보여준다. 어느 탭을 보일지는 에디터 화면(EditorPage)이 정한다
 * (문구 상자를 누르면 텍스트 편집기 탭으로 넘어가는 등).
 *
 * @param props - 지금 탭, 탭 변경 함수, AI 추천 탭 내용, 텍스트 편집기 탭 내용
 * @returns 탭 패널
 */
export default function EditorSidePanel({ tab, onTabChange, ai, children }: EditorSidePanelProps) {
  const baseId = useId();

  return (
    <aside className={styles.panel}>
      <div className={styles.tabs} role="tablist" aria-label="문구 편집">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`${baseId}-${id}-tab`}
            aria-selected={tab === id}
            aria-controls={`${baseId}-${id}-panel`}
            className={`${styles.tab} ${tab === id ? styles.active : ""}`}
            onClick={() => onTabChange(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`${baseId}-${tab}-panel`}
        aria-labelledby={`${baseId}-${tab}-tab`}
        className={styles.content}
      >
        {tab === "text" ? children : ai}
      </div>
    </aside>
  );
}
