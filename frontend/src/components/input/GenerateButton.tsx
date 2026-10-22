/**
 * 이미지 생성 버튼 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import type { HealthResponse } from "../../api/client";
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
  /** 서버 상태. 받았으면 버튼 아래에 생성 장수와 예상 시간을 안내한다 */
  health: HealthResponse | null;
}

/**
 * 생성 장수와 예상 시간 안내 문구를 만든다.
 * 실제 모델은 4장에 약 1분이 걸리고(GPU 서버 측정), mock은 바로 끝나 시간을 안내하지 않는다.
 *
 * @param health - 서버 상태
 * @returns 안내 문구
 */
function toHint(health: HealthResponse): string {
  const count = `한 번에 ${health.num_images_per_request}장을 만들어요`;
  return health.image_generator === "mock" ? count : `${count} · 약 1분 걸려요`;
}

/**
 * 모든 입력 옵션 맨 아래에 놓이는 [이미지 생성] 버튼과 생성 장수 안내.
 * 마우스를 올리면 단축키(Ctrl+Enter / ⌘+Enter)를 툴팁으로 안내한다.
 *
 * @param props - 비활성 여부, 생성 중 여부, 클릭 처리 함수, 서버 상태
 * @returns 가운데 정렬된 생성 버튼
 */
export default function GenerateButton({
  disabled,
  loading,
  onClick,
  health,
}: GenerateButtonProps) {
  return (
    <div className={styles.wrapper}>
      <Button variant="primary" disabled={disabled} title={SHORTCUT_LABEL} onClick={onClick}>
        {loading ? "생성 중..." : "이미지 생성"}
      </Button>
      {health && <p className={styles.hint}>{toHint(health)}</p>}
    </div>
  );
}
