/**
 * 이미지 생성 중 화면 전체를 덮는 로딩 화면 컴포넌트.
 *
 * 생성일자: 2026-11-02
 * 생성자: bioyejin
 * 수정일자: 2026-11-02
 * 수정자: bioyejin
 */

import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { GenerationProgress } from "../../hooks/useGeneration";
import Button from "../common/Button";
import styles from "./LoadingOverlay.module.css";

/** 첫 step이 끝나기 전에는 step 시간을 모르므로 이 시간 동안 이 위치까지 채운다 */
const FIRST_STEP_GUESS_MS = 2000;
const FIRST_STEP_GUESS_RATIO = 0.1;
/** 마지막 step이 끝났을 때 끝까지 채우는 시간 */
const FINISH_MS = 300;
/** "생성 중" 뒤 점이 하나씩 늘어나는 간격 */
const DOTS_INTERVAL_MS = 500;

/** 진행 막대의 목표 위치(0~1)와 그 위치까지 채우는 데 걸리는 시간 */
interface BarTarget {
  ratio: number;
  durationMs: number;
}

/**
 * 끊어서 오는 step 진행률을 막대가 서서히 차도록 바꾼다.
 * step이 올 때마다 지난 step에 걸린 시간을 재고, 그 시간 동안 다음 step 위치까지 채운다.
 * 다음 step이 늦으면 막대는 그 위치에서 기다리므로 실제보다 한 step 넘게 앞서지 않는다.
 *
 * @param progress - 생성 진행 상황
 * @returns 진행 막대의 목표 위치와 채우는 시간
 */
function useSmoothProgress(progress: GenerationProgress | null): BarTarget {
  const [target, setTarget] = useState<BarTarget>({ ratio: 0, durationMs: 0 });
  // 마지막으로 받은 step과 받은 시각
  const lastStepRef = useRef<{ step: number; at: number } | null>(null);

  const stage = progress?.stage;
  const step = progress?.step ?? null;
  const total = progress?.total ?? null;

  useEffect(() => {
    // 번역 중, 대기 중에는 비워 둔다
    if (stage !== "generating") {
      lastStepRef.current = null;
      setTarget({ ratio: 0, durationMs: 0 });
      return;
    }
    const now = performance.now();
    // 생성은 시작했지만 첫 step이 아직 끝나지 않음
    if (step === null || total === null) {
      lastStepRef.current = { step: 0, at: now };
      setTarget({ ratio: FIRST_STEP_GUESS_RATIO, durationMs: FIRST_STEP_GUESS_MS });
      return;
    }
    // 모든 step이 끝나고 이미지 마무리 중
    if (step >= total) {
      setTarget({ ratio: 1, durationMs: FINISH_MS });
      return;
    }
    const last = lastStepRef.current;
    const msPerStep =
      last && step > last.step ? (now - last.at) / (step - last.step) : FIRST_STEP_GUESS_MS;
    lastStepRef.current = { step, at: now };
    setTarget({ ratio: (step + 1) / total, durationMs: msPerStep });
  }, [stage, step, total]);

  return target;
}

export interface LoadingOverlayProps {
  /** 생성 진행 상황. 작업 등록 전이면 null */
  progress: GenerationProgress | null;
  onCancel: () => void;
}

/**
 * "생성 중..." 문구, 서서히 차는 진행 막대, 생성 취소 버튼을 화면 가운데에 보여준다.
 * 화면 전체를 덮어 생성 중에는 취소 버튼만 누를 수 있다.
 *
 * @param props - 생성 진행 상황과 취소 처리 함수
 * @returns body 위에 그려지는 로딩 화면
 */
export default function LoadingOverlay({ progress, onCancel }: LoadingOverlayProps) {
  const titleId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [dots, setDots] = useState(1);
  const bar = useSmoothProgress(progress);

  // 뒤 화면이 키보드로 눌리지 않도록 취소 버튼에 포커스
  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  // 점 개수를 1 → 2 → 3 → 1 … 로 바꾼다
  useEffect(() => {
    const timer = window.setInterval(() => setDots((count) => (count % 3) + 1), DOTS_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, []);

  // 화면 읽기 프로그램에는 막대 애니메이션이 아니라 실제 step 진행률을 알린다
  const percent =
    progress?.step != null && progress.total
      ? Math.round((progress.step / progress.total) * 100)
      : 0;

  return createPortal(
    <div className={styles.backdrop}>
      <div className={styles.content} role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <p id={titleId} className={styles.title}>
          생성 중
          <span className={styles.dots} aria-hidden>
            {".".repeat(dots)}
          </span>
        </p>
        <p className={styles.message}>조금만 기다려 주세요!</p>
        <div
          className={styles.track}
          role="progressbar"
          aria-label="생성 진행률"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
        >
          <div
            className={styles.fill}
            style={{
              transform: `scaleX(${bar.ratio})`,
              transitionDuration: `${bar.durationMs}ms`,
            }}
          />
        </div>
        <Button ref={cancelRef} variant="secondary" onClick={onCancel}>
          생성 취소
        </Button>
      </div>
    </div>,
    document.body,
  );
}
