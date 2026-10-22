/**
 * 서버 상태 배지 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "../../api/client";
import styles from "./ServerStatusBadge.module.css";

/** 조회 결과: 확인 중 / 응답 받음 / 연결 실패 */
type ServerStatus =
  | { kind: "loading" }
  | { kind: "ok"; health: HealthResponse }
  | { kind: "error" };

/** 점 색: 확인 중(빈 점), 회색(mock), 초록(실제 모델), 빨강(연결 실패) */
type Tone = "pending" | "muted" | "success" | "danger";

/**
 * 조회 결과를 배지에 표시할 문구와 점 색으로 바꾼다.
 *
 * @param status - 서버 상태 조회 결과
 * @returns 표시 문구와 점 색
 */
function toBadge(status: ServerStatus): { label: string; tone: Tone } {
  if (status.kind === "loading") return { label: "확인 중", tone: "pending" };
  if (status.kind === "error") return { label: "서버 연결 안 됨", tone: "danger" };

  const { image_generator: mode, num_images_per_request: count } = status.health;
  // 처음 보는 모드가 와도 깨지지 않도록 값을 그대로 대문자로 표시한다
  return {
    label: `${mode.toUpperCase()} · ${count}장`,
    tone: mode === "mock" ? "muted" : "success",
  };
}

/**
 * 화면을 열 때 /api/health를 한 번 조회해 이미지 생성 모드와 장수를 보여주는 배지.
 *
 * @returns 점과 문구로 된 배지
 */
export default function ServerStatusBadge() {
  const [status, setStatus] = useState<ServerStatus>({ kind: "loading" });

  useEffect(() => {
    // 화면을 벗어난 뒤 늦게 도착한 응답은 무시한다
    let ignore = false;
    fetchHealth()
      .then((health) => {
        if (!ignore) setStatus({ kind: "ok", health });
      })
      .catch(() => {
        if (!ignore) setStatus({ kind: "error" });
      });
    return () => {
      ignore = true;
    };
  }, []);

  const { label, tone } = toBadge(status);

  return (
    <span className={styles.badge} role="status" title="이미지 생성 서버 상태">
      <span className={`${styles.dot} ${styles[tone]}`} aria-hidden />
      {label}
    </span>
  );
}
