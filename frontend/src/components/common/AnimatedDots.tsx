/**
 * "생성 중..."처럼 문구 뒤에서 점이 1 → 2 → 3개로 움직이는 컴포넌트.
 *
 * 생성일자: 2026-11-10
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { useEffect, useState } from "react";
import styles from "./AnimatedDots.module.css";

/** 점이 하나씩 늘어나는 간격 */
const DOTS_INTERVAL_MS = 500;

/**
 * 점 개수를 1 → 2 → 3 → 1 … 로 바꿔 진행 중임을 보여준다.
 * 점 3개 자리를 미리 잡아 두어 앞 글자가 움직이지 않는다. 화면 낭독기는 읽지 않는다.
 *
 * @returns 움직이는 점
 */
export default function AnimatedDots() {
  const [dots, setDots] = useState(1);

  useEffect(() => {
    const timer = window.setInterval(() => setDots((count) => (count % 3) + 1), DOTS_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <span className={styles.dots} aria-hidden>
      {".".repeat(dots)}
    </span>
  );
}
