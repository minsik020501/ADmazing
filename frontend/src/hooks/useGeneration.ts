/**
 * 이미지 생성 진행 상태와 취소를 관리하는 훅.
 *
 * 생성일자: 2026-11-02
 * 생성자: bioyejin
 * 수정일자: 2026-11-02
 * 수정자: bioyejin
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelGenerationJob,
  createGenerationJob,
  subscribeGenerationJob,
  type GenerateOptions,
  type GenerateResponse,
  type GenerationJobStatus,
} from "../api/client";

/** 생성 중 진행 상황. 로딩 화면의 진행 막대에 쓴다 */
export type GenerationProgress = Pick<GenerationJobStatus, "stage" | "step" | "total">;

export interface Generation {
  /** 생성 중이면 true (작업 등록부터 끝날 때까지) */
  running: boolean;
  /** 생성 중 진행 상황. 작업 등록 전이나 생성 중이 아니면 null */
  progress: GenerationProgress | null;
  result: GenerateResponse | null;
  error: string | null;
  /** 마지막 생성을 사용자가 취소했으면 true */
  cancelled: boolean;
  /** 마지막으로 생성을 시작할 때 쓴 옵션. 결과 화면의 옵션 요약과 다시 생성에 쓴다 */
  options: GenerateOptions | null;
  /** 생성을 시작한다. 이전 결과, 에러, 취소 표시는 지운다 */
  start: (options: GenerateOptions) => Promise<void>;
  /** 마지막으로 생성할 때 쓴 옵션 그대로 다시 생성한다 (seed는 서버가 새로 정함) */
  regenerate: () => void;
  /** 생성 중이면 바로 멈추고 서버에도 취소를 요청한다 */
  cancel: () => void;
  /** 생성 중이면 멈추고 결과, 에러, 취소 표시를 모두 지운다 */
  reset: () => void;
}

/**
 * 생성 작업 등록 → 진행 상황 구독 → 결과/에러/취소 반영을 한곳에서 관리한다.
 * 생성 중에 탭을 닫으면 서버에 취소를 요청한다 (서버는 연결이 끊겨도 생성을 계속하기 때문).
 *
 * @returns 생성 상태와 시작·취소·초기화 함수
 */
export default function useGeneration(): Generation {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelled, setCancelled] = useState(false);
  const [options, setOptions] = useState<GenerateOptions | null>(null);

  // 생성할 때마다 1씩 늘려, 취소되었거나 지난 생성에서 늦게 도착한 응답을 무시한다
  const runIdRef = useRef(0);
  // 진행 중인 작업 id (작업 등록 전이거나 생성 중이 아니면 null)
  const jobIdRef = useRef<string | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  /** 진행 중인 생성을 화면에서 정리한다. 서버 취소 요청은 하지 않는다. */
  const stop = useCallback(() => {
    runIdRef.current += 1;
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
    jobIdRef.current = null;
    setRunning(false);
    setProgress(null);
  }, []);

  /** 진행 중인 작업이 있으면 서버에 취소를 요청하고 화면에서 정리한다. */
  const abort = useCallback(() => {
    const jobId = jobIdRef.current;
    stop();
    if (jobId) {
      cancelGenerationJob(jobId).catch((err) => {
        // 화면은 이미 취소된 상태라 사용자에게는 알리지 않고 원인만 남긴다
        console.error("생성 취소 요청 실패", err);
      });
    }
  }, [stop]);

  const start = useCallback(
    async (nextOptions: GenerateOptions) => {
      abort();
      const runId = runIdRef.current;
      setRunning(true);
      setResult(null);
      setError(null);
      setCancelled(false);
      setOptions(nextOptions);

      let jobId: string;
      try {
        jobId = await createGenerationJob(nextOptions);
      } catch (err) {
        if (runIdRef.current !== runId) return;
        stop();
        setError(err instanceof Error ? err.message : String(err));
        return;
      }
      // 작업이 등록되는 사이에 취소했으면 방금 만든 작업도 취소한다
      if (runIdRef.current !== runId) {
        cancelGenerationJob(jobId).catch((err) => console.error("생성 취소 요청 실패", err));
        return;
      }

      jobIdRef.current = jobId;
      unsubscribeRef.current = subscribeGenerationJob(
        jobId,
        (status) => {
          if (runIdRef.current !== runId) return;
          if (status.stage === "done") {
            stop();
            setResult(status.result);
          } else if (status.stage === "failed") {
            stop();
            setError(status.error ?? "이미지를 생성하지 못했습니다.");
          } else if (status.stage === "cancelled") {
            stop();
            setCancelled(true);
          } else {
            setProgress({ stage: status.stage, step: status.step, total: status.total });
          }
        },
        (message) => {
          if (runIdRef.current !== runId) return;
          stop();
          setError(message);
        },
      );
    },
    [abort, stop],
  );

  const regenerate = useCallback(() => {
    if (options) start(options);
  }, [options, start]);

  const cancel = useCallback(() => {
    abort();
    setCancelled(true);
  }, [abort]);

  const reset = useCallback(() => {
    abort();
    setResult(null);
    setError(null);
    setCancelled(false);
    setOptions(null);
  }, [abort]);

  // 생성 중에 탭을 닫으면 서버에 취소를 요청한다. 화면을 벗어나면 구독도 닫는다
  useEffect(() => {
    function handlePageHide() {
      const jobId = jobIdRef.current;
      if (jobId) {
        // keepalive: 페이지가 닫히는 중에도 요청이 끝까지 전송되게 한다.
        // 페이지가 이미 닫히는 중이라 실패해도 할 수 있는 일이 없다
        cancelGenerationJob(jobId, true).catch(() => {});
      }
    }
    window.addEventListener("pagehide", handlePageHide);
    return () => {
      window.removeEventListener("pagehide", handlePageHide);
      unsubscribeRef.current?.();
    };
  }, []);

  return {
    running,
    progress,
    result,
    error,
    cancelled,
    options,
    start,
    regenerate,
    cancel,
    reset,
  };
}
