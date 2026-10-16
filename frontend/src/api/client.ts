/**
 * 백엔드 API 클라이언트.
 *
 * 생성일자: 2026-10-16
 * 생성자: ven_choi
 * 수정일자: 2026-10-16
 * 수정자: ven_choi
 */

/** 이미지 생성 API 응답 */
export interface GenerateResponse {
  original_prompt: string;
  translated_prompt: string;
  image_base64: string;
}

/**
 * 한국어 프롬프트로 광고 이미지 생성을 요청한다.
 *
 * @param prompt - 한국어 광고 이미지 설명
 * @returns 원본 프롬프트, 번역된 프롬프트, PNG base64 이미지
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
    throw new Error(body?.detail ?? `요청 실패 (${res.status})`);
  }
  return res.json();
}
