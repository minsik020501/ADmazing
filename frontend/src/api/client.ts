/**
 * 백엔드 API 클라이언트.
 *
 * 생성일자: 2026-10-16
 * 생성자: ven_choi
 * 수정일자: 2026-11-06
 * 수정자: bioyejin
 */

import type { CopyRequestRow } from "../constants/copyRequests";
import { STYLE_PRESETS } from "../constants/stylePresets";

/** 추천 문구 하나 */
export interface CopySuggestion {
  text: string;
  /** user: 사용자가 직접 넣은 문장, ai: AI가 추천한 문구 */
  source: "user" | "ai";
}

/** 이미지 한 장에 어울리는 역할별 추천 문구 (역할마다 최대 5개) */
export interface ImageCopies {
  title: CopySuggestion[];
  subtitle: CopySuggestion[];
  text: CopySuggestion[];
}

/** 생성된 이미지 한 장 */
export interface GeneratedImage {
  /** PNG 이미지의 base64 문자열 */
  image_base64: string;
  /** 이 이미지를 생성한 seed (같은 seed로 다시 요청하면 같은 이미지) */
  seed: number;
  /** 이 이미지에 맞춘 추천 문구. 추천에 실패하면 null */
  copies: ImageCopies | null;
  /** 문구 추천에 실패했을 때 화면에 보여줄 메시지 */
  copies_error: string | null;
}

/** 이미지 생성 API 응답 */
export interface GenerateResponse {
  original_prompt: string;
  translated_prompt: string;
  /** 요청한 이미지 비율 (예: "16:9") */
  ratio: string;
  /** 서버가 비율에 맞춰 정한 해상도(px) */
  width: number;
  height: number;
  /** 서버 설정(NUM_IMAGES_PER_REQUEST)만큼 생성된 이미지 목록 */
  images: GeneratedImage[];
}

/**
 * 생성 작업 단계.
 * translating: 번역 중, queued: 앞선 생성 대기 중, generating: 생성 중,
 * recommending_copy: 이미지별 문구 추천 중, done: 완료, failed: 실패, cancelled: 취소됨
 */
export type JobStage =
  | "translating"
  | "queued"
  | "generating"
  | "recommending_copy"
  | "done"
  | "failed"
  | "cancelled";

/** 생성 작업 상태. 진행 상황 스트림(SSE)에서 상태가 바뀔 때마다 받는다 */
export interface GenerationJobStatus {
  job_id: string;
  stage: JobStage;
  /** 완료한 디노이징 step 수. step == total이면 이미지 마무리(디코딩) 중 */
  step: number | null;
  /** 전체 디노이징 step 수 */
  total: number | null;
  /** 문구 추천이 끝난 이미지 수 (성공·실패 모두). recommending_copy 전에는 null */
  copy_done: number | null;
  /** 문구를 추천할 이미지 수. recommending_copy 전에는 null */
  copy_total: number | null;
  /** stage가 done일 때 결과 */
  result: GenerateResponse | null;
  /** stage가 failed일 때 에러 메시지 */
  error: string | null;
}

/** 작업이 끝난 단계. 이 단계를 받으면 진행 상황 스트림이 닫힌다 */
const FINISHED_STAGES: JobStage[] = ["done", "failed", "cancelled"];

/** 서버 상태 조회 API 응답 */
export interface HealthResponse {
  status: "ok";
  /** 이미지 생성 모드. 현재 서버는 mock, diffusers, sdxl, zimage 중 하나를 보낸다 */
  image_generator: string;
  model_path: string;
  lora_path: string | null;
  /** 요청 한 번에 생성되는 이미지 장수 */
  num_images_per_request: number;
}

/**
 * 에러 응답의 detail을 화면에 보여줄 문구로 바꾼다.
 * 서버는 detail을 문자열(예: 503 GPU 메모리 부족)이나
 * 검증 에러 배열(422, 각 항목의 msg가 한국어 메시지)로 보낸다.
 *
 * @param detail - 에러 응답 본문의 detail 값
 * @param status - HTTP 상태 코드
 * @returns 화면에 보여줄 에러 문구
 */
function toErrorMessage(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((msg): msg is string => typeof msg === "string");
    if (messages.length > 0) return messages.join("\n");
  }
  return `요청 실패 (${status})`;
}

/** 화면에서 고른 생성 옵션 */
export interface GenerateOptions {
  /** 한국어 광고 이미지 설명 */
  prompt: string;
  /** 스타일 id (constants/stylePresets.ts) */
  styleId: string;
  /** 비율 (constants/imageRatios.ts, 서버 허용값과 같음) */
  ratio: string;
  /** 삽입할 문구 입력 줄. AI가 문구를 추천할 때 참고한다 */
  copyRequests: CopyRequestRow[];
}

/**
 * 서버로 보낼 프롬프트를 만든다. 서버에 스타일 항목이 없어 스타일 문구를 프롬프트 뒤에 붙인다.
 *
 * @param prompt - 입력한 프롬프트
 * @param styleId - 고른 스타일 id
 * @returns 스타일 문구가 붙은 프롬프트
 */
function buildPrompt(prompt: string, styleId: string): string {
  const style = STYLE_PRESETS.find((preset) => preset.id === styleId);
  return style?.suffix ? `${prompt.trim()}, ${style.suffix}` : prompt;
}

/**
 * 화면에서 고른 옵션을 서버 요청 본문으로 바꾼다.
 * 화면 옵션을 서버 요청 형식으로 바꾸는 일은 이 함수에서만 한다.
 *
 * 비어 있는 문구 줄은 보내지 않고, 내용이 있는 줄이 하나도 없으면 copy_requests를 넣지 않는다.
 *
 * @param options - 프롬프트, 스타일, 비율, 문구 입력 줄
 * @returns JSON 문자열로 된 요청 본문
 */
function toRequestBody(options: GenerateOptions): string {
  const copyRequests = options.copyRequests
    .map((row) => [row.role, row.text.trim()])
    .filter(([, text]) => text !== "");
  return JSON.stringify({
    prompt: buildPrompt(options.prompt, options.styleId),
    ratio: options.ratio,
    ...(copyRequests.length > 0 && { copy_requests: Object.fromEntries(copyRequests) }),
  });
}

/**
 * 이미지 생성 작업을 등록한다. 서버는 생성을 기다리지 않고 바로 작업 id를 돌려준다.
 *
 * @param options - 프롬프트, 스타일, 비율, 문구 입력 줄
 * @returns 진행 상황 조회와 취소에 쓰는 작업 id
 * @throws {Error} 응답 상태가 2xx가 아닐 때 (예: 422 입력 검증 실패)
 */
export async function createGenerationJob(options: GenerateOptions): Promise<string> {
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: toRequestBody(options),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(toErrorMessage(body?.detail, res.status));
  }
  const body: { job_id: string } = await res.json();
  return body.job_id;
}

/**
 * 작업의 진행 상황을 구독한다. 상태가 바뀔 때마다 onStatus가 호출되고,
 * 작업이 끝나면(done, failed, cancelled) 구독이 자동으로 닫힌다.
 *
 * @param jobId - 작업 id
 * @param onStatus - 새 상태를 받을 때마다 호출
 * @param onError - 서버 연결이 끊겨 더 받을 수 없을 때 호출
 * @returns 구독을 닫는 함수
 */
export function subscribeGenerationJob(
  jobId: string,
  onStatus: (status: GenerationJobStatus) => void,
  onError: (message: string) => void,
): () => void {
  const source = new EventSource(`/api/jobs/${jobId}/events`);
  source.onmessage = (event) => {
    const status: GenerationJobStatus = JSON.parse(event.data);
    // 서버가 스트림을 닫으면 브라우저가 다시 연결하려 하므로 끝난 작업은 먼저 닫는다
    if (FINISHED_STAGES.includes(status.stage)) source.close();
    onStatus(status);
  };
  source.onerror = () => {
    // 잠깐 끊긴 경우에는 브라우저가 알아서 다시 연결한다(CONNECTING).
    // CLOSED는 다시 연결하지 않는 경우(작업이 없음, 서버 응답 에러 등)
    if (source.readyState === EventSource.CLOSED) {
      onError("서버와 연결이 끊겨 진행 상황을 받지 못했습니다. 잠시 후 다시 시도해 주세요.");
    }
  };
  return () => source.close();
}

/**
 * 작업 취소를 요청한다. 이미 끝난 작업이면 서버에서 아무 일도 하지 않는다.
 *
 * @param jobId - 작업 id
 * @param keepalive - 탭을 닫는 중에도 요청이 끝까지 전송되게 할지 여부
 * @throws {Error} 응답 상태가 2xx가 아닐 때
 */
export async function cancelGenerationJob(jobId: string, keepalive = false): Promise<void> {
  const res = await fetch(`/api/jobs/${jobId}`, { method: "DELETE", keepalive });
  if (!res.ok) {
    throw new Error(`요청 실패 (${res.status})`);
  }
}

/**
 * 서버 상태와 이미지 생성 설정을 조회한다.
 *
 * @returns 서버 상태, 이미지 생성 모드, 요청당 이미지 장수 등
 * @throws {Error} 응답 상태가 2xx가 아닐 때
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch("/api/health");
  if (!res.ok) {
    throw new Error(`요청 실패 (${res.status})`);
  }
  return res.json();
}
