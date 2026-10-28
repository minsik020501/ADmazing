/**
 * 백엔드 API 클라이언트.
 *
 * 생성일자: 2026-10-16
 * 생성자: ven_choi
 * 수정일자: 2026-10-28
 * 수정자: ven_choi
 */

/** 생성된 이미지 한 장 */
export interface GeneratedImage {
  /** PNG 이미지의 base64 문자열 */
  image_base64: string;
  /** 이 이미지를 생성한 seed (같은 seed로 다시 요청하면 같은 이미지) */
  seed: number;
}

/** 이미지 생성 API 응답 */
export interface GenerateResponse {
  original_prompt: string;
  translated_prompt: string;
  /** 서버 설정(NUM_IMAGES_PER_REQUEST)만큼 생성된 이미지 목록 */
  images: GeneratedImage[];
}

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

/**
 * 한국어 프롬프트로 광고 이미지 생성을 요청한다.
 *
 * @param prompt - 한국어 광고 이미지 설명
 * @returns 원본 프롬프트, 번역된 프롬프트, 생성된 이미지와 seed 목록
 * @throws {Error} 응답 상태가 2xx가 아닐 때
 */
export async function generateImage(prompt: string): Promise<GenerateResponse> {
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(toErrorMessage(body?.detail, res.status));
  }
  return res.json();
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
