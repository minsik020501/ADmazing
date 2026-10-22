/**
 * 이미지 생성 버튼 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import Button from "../common/Button";
import styles from "./GenerateButton.module.css";

/** Mac에서는 Ctrl 대신 ⌘(Command) 키를 안내한다 */
const SHORTCUT_LABEL = /Mac|iPhone|iPad/.test(navigator.userAgent) ? "⌘ + Enter" : "Ctrl + Enter";

export interface GenerateButtonProps {
  /** 입력이 비었거나 생성 중이면 true */
  disabled: boolean;
  /** 생성 중이면 "생성 중..."을 표시 */
  loading: boolean;
  onClick: () => void;
}

/**
 * 모든 입력 옵션 맨 아래에 놓이는 [이미지 생성] 버튼.
 * 마우스를 올리면 단축키(Ctrl+Enter / ⌘+Enter)를 툴팁으로 안내한다.
 *
 * @param props - 비활성 여부, 생성 중 여부, 클릭 처리 함수
 * @returns 가운데 정렬된 생성 버튼
 */
export default function GenerateButton({ disabled, loading, onClick }: GenerateButtonProps) {
  return (
    <div className={styles.wrapper}>
      <Button variant="primary" disabled={disabled} title={SHORTCUT_LABEL} onClick={onClick}>
        {loading ? "생성 중..." : "이미지 생성"}
      </Button>
    </div>
  );
}
