/**
 * 화면의 이미지를 파일로 내려받는 함수 모음.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

import { EDITED_FILE_SUFFIX, IMAGE_FILE_PREFIX } from "../../constants/editor";

// 다운로드가 시작되기 전에 주소가 지워지지 않도록, 클릭하고 잠시 뒤에 정리한다
const REVOKE_DELAY_MS = 1000;

/**
 * 내려받을 이미지 파일 이름을 만든다.
 *
 * @param seed - 이미지를 생성한 seed
 * @param edited - 문구를 넣은 편집본이면 true
 * @returns 파일 이름. 예: "admazing_seed42.png", "admazing_seed42_edited.png"
 */
export function toImageFileName(seed: number, edited = false): string {
  const suffix = edited ? `_${EDITED_FILE_SUFFIX}` : "";
  return `${IMAGE_FILE_PREFIX}_seed${seed}${suffix}.png`;
}

/**
 * 서버가 보낸 base64 문자열을 파일 데이터(Blob)로 바꾼다.
 *
 * @param base64 - 이미지의 base64 문자열 (data: 접두어 없이)
 * @param type - 파일 형식
 * @returns 이미지 Blob
 */
export function base64ToBlob(base64: string, type = "image/png"): Blob {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type });
}

/**
 * 파일 데이터를 브라우저 다운로드로 저장한다.
 * 큰 이미지도 저장되도록 data: 주소 대신 임시 파일 주소(blob:)를 쓴다.
 *
 * @param blob - 저장할 파일 데이터
 * @param fileName - 저장할 파일 이름
 */
export function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), REVOKE_DELAY_MS);
}
