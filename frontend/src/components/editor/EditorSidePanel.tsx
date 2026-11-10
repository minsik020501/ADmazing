/**
 * 에디터 오른쪽의 탭 패널 컴포넌트.
 *
 * 생성일자: 2026-11-05
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { useId, useState, type ReactNode } from "react";
import styles from "./EditorSidePanel.module.css";

type PanelTab = "ai" | "text";

const TABS: { id: PanelTab; label: string }[] = [
  { id: "ai", label: "AI 추천" },
  { id: "text", label: "텍스트 편집기" },
];

export interface EditorSidePanelProps {
  /** [AI 추천] 탭 내용 */
  ai: ReactNode;
  /** [텍스트 편집기] 탭 내용 */
  children: ReactNode;
}

/**
 * [AI 추천], [텍스트 편집기] 탭을 보여준다. 에디터를 열면 AI 추천 탭부터 보인다.
 *
 * @param props - AI 추천 탭 내용, 텍스트 편집기 탭 내용
 * @returns 탭 패널
 */
export default function EditorSidePanel({ ai, children }: EditorSidePanelProps) {
  const [tab, setTab] = useState<PanelTab>("ai");
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
            onClick={() => setTab(id)}
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
