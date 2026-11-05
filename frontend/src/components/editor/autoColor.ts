/**
 * 이미지 밝기에 맞춰 잘 보이는 글자색을 고르는 함수.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

// 밝기를 잴 때 이미지를 줄여 그리는 크기 (정확할 필요가 없어 작게)
const SAMPLE_SIZE = 64;
// 이보다 밝으면(0~1) 검은 글자, 어두우면 흰 글자
const BRIGHT_THRESHOLD = 0.55;
// 문구가 놓일 자리로 보고 밝기를 재는 범위 (위치 기준 가로·세로 ± 비율)
const AREA_HALF_WIDTH = 0.25;
const AREA_HALF_HEIGHT = 0.08;

/**
 * 이미지의 (x, y) 둘레 평균 밝기를 보고 글자색을 고른다. 밝으면 검정, 어두우면 흰색.
 *
 * @param base64 - PNG 이미지의 base64 문자열
 * @param x - 문구 가운데 위치 (이미지 가로 대비 비율)
 * @param y - 문구 가운데 위치 (이미지 세로 대비 비율)
 * @returns "#000000" 또는 "#FFFFFF". 이미지를 읽지 못하면 흰색
 */
export async function pickTextColor(base64: string, x: number, y: number): Promise<string> {
  try {
    const image = new Image();
    image.src = `data:image/png;base64,${base64}`;
    await image.decode();

    const canvas = document.createElement("canvas");
    canvas.width = SAMPLE_SIZE;
    canvas.height = SAMPLE_SIZE;
    const context = canvas.getContext("2d");
    if (!context) return "#FFFFFF";
    context.drawImage(image, 0, 0, SAMPLE_SIZE, SAMPLE_SIZE);

    const toPixel = (ratio: number) =>
      Math.min(SAMPLE_SIZE - 1, Math.max(0, Math.round(ratio * SAMPLE_SIZE)));
    const left = toPixel(x - AREA_HALF_WIDTH);
    const top = toPixel(y - AREA_HALF_HEIGHT);
    const right = toPixel(x + AREA_HALF_WIDTH);
    const bottom = toPixel(y + AREA_HALF_HEIGHT);
    const { data } = context.getImageData(left, top, right - left + 1, bottom - top + 1);

    let sum = 0;
    for (let i = 0; i < data.length; i += 4) {
      // 사람 눈에 보이는 밝기 (초록이 가장 밝게 보임)
      sum += 0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2];
    }
    const brightness = sum / (data.length / 4) / 255;
    return brightness > BRIGHT_THRESHOLD ? "#000000" : "#FFFFFF";
  } catch {
    // 밝기를 못 재도 문구 추가는 되어야 하므로 기본색을 쓴다
    return "#FFFFFF";
  }
}
