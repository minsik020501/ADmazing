/**
 * 백엔드 API 클라이언트.
 *
 * 생성일자: 2026-10-16
 * 생성자: ven_choi
 * 수정일자: 2026-10-28
 * 수정자: ven_choi
 */

import { STYLE_PRESETS } from "../constants/stylePresets";

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
  /** 요청한 이미지 비율 (예: "16:9") */
  ratio: string;
  /** 서버가 비율에 맞춰 정한 해상도(px) */
  width: number;
  height: number;
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

/** 화면에서 고른 생성 옵션 */
export interface GenerateOptions {
  /** 한국어 광고 이미지 설명 */
  prompt: string;
  /** 스타일 id (constants/stylePresets.ts) */
  styleId: string;
  /** 비율 (constants/imageRatios.ts, 서버 허용값과 같음) */
  ratio: string;
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
 * 화면에서 고른 옵션으로 광고 이미지 생성을 요청한다.
 * 화면 옵션을 서버 요청 형식으로 바꾸는 일은 이 함수에서만 한다.
 *
 * @param options - 프롬프트, 스타일, 비율
 * @returns 원본 프롬프트, 번역된 프롬프트, 비율과 해상도, 생성된 이미지와 seed 목록
 * @throws {Error} 응답 상태가 2xx가 아닐 때
 */
export async function generateImage(options: GenerateOptions): Promise<GenerateResponse> {
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: buildPrompt(options.prompt, options.styleId),
      ratio: options.ratio,
    }),
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
