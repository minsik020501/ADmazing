/**
 * 좌측 패널(서랍) 컴포넌트.
 *
 * 생성일자: 2026-10-20
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { Plus, X } from "lucide-react";
import Button from "../common/Button";
import styles from "./Sidebar.module.css";

export interface SidebarProps {
  /** 패널이 열렸는지 여부 */
  open: boolean;
  /** 닫기 버튼, 바깥 영역 클릭 시 호출 */
  onClose: () => void;
  /** 입력값과 결과를 비우고 처음 상태로 돌아가기 */
  onNewProject: () => void;
}

/**
 * 제목과 새로 만들기 버튼이 있는 좌측 패널.
 * 메인 화면 위에 서랍처럼 겹쳐 열리고, 닫기 버튼이나 바깥 영역을 누르면 닫힌다.
 * 생성 기록(히스토리) 목록은 구현 가능하지만 프로젝트 일정상 미구현해 주석으로 숨겨 두었다.
 *
 * @param props - 열림 상태와 닫기·새로 만들기 처리 함수
 * @returns 좌측 패널(열렸을 때는 뒤 배경 포함)
 */
export default function Sidebar({ open, onClose, onNewProject }: SidebarProps) {
  const classes = [styles.sidebar, open && styles.open].filter(Boolean).join(" ");

  return (
    <>
      {open && <div className={styles.backdrop} onClick={onClose} />}
      <aside className={classes} aria-hidden={!open}>
        <div className={styles.header}>
          <h2 className={styles.title}>Menu</h2>
          <Button
            variant="ghost"
            size="sm"
            icon={<X size={16} />}
            aria-label="패널 닫기"
            onClick={onClose}
          />
        </div>

        <Button
          variant="secondary"
          className={styles.newButton}
          icon={<Plus size={16} />}
          onClick={onNewProject}
        >
          새로 만들기
        </Button>

        {/*
          생성 기록(히스토리): 구현 가능하지만 프로젝트 일정상 미구현.
          이전 생성 결과를 저장해 다시 열어 보는 목록이 들어갈 자리로, 스타일은
          Sidebar.module.css의 .history, .empty에 남겨 두었다.
        <nav className={styles.history} aria-label="생성 기록">
          <p className={styles.empty}>아직 생성 기록이 없어요</p>
        </nav>
        */}
      </aside>
    </>
  );
}
