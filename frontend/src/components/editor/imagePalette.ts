/**
 * 이미지 대표색 뽑기와, 에디터의 색 고르기 칸에 대표색을 넘기는 context.
 *
 * 생성일자: 2026-11-10
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { createContext, useEffect, useState } from "react";
import type { GeneratedImage } from "../../api/client";
import { IMAGE_PALETTE } from "../../constants/editor";

/** OKLab 색 좌표 (L: 밝기, a·b: 색조와 채도) */
type Lab = [l: number, a: number, b: number];

/** 대표색 후보 하나: 비슷한 색을 묶은 평균색과 이미지에서 차지하는 비율 */
interface Candidate {
  hex: string;
  lab: Lab;
  share: number;
}

/**
 * sRGB 채널 값(0~255)을 빛의 세기에 비례하는 값(0~1)으로 바꾼다.
 *
 * @param value - 채널 값
 * @returns 선형 값
 */
function toLinear(value: number): number {
  const c = value / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

/**
 * RGB를 OKLab으로 바꾼다. OKLab에서는 두 색의 거리가 사람 눈에 보이는 차이와 비슷하다.
 *
 * @param r - 빨강 (0~255)
 * @param g - 초록 (0~255)
 * @param b - 파랑 (0~255)
 * @returns OKLab 좌표
 */
function toOklab(r: number, g: number, b: number): Lab {
  const [lr, lg, lb] = [toLinear(r), toLinear(g), toLinear(b)];
  const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
  const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
  const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

/**
 * 두 색의 OKLab 거리. 밝기·색조·채도 차이를 모두 반영한다.
 *
 * @param x - 색 하나
 * @param y - 다른 색
 * @returns 거리
 */
function distance(x: Lab, y: Lab): number {
  return Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]);
}

/**
 * RGB를 #RRGGBB로 바꾼다.
 *
 * @param r - 빨강 (0~255)
 * @param g - 초록 (0~255)
 * @param b - 파랑 (0~255)
 * @returns #RRGGBB
 */
function toHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("")}`.toUpperCase();
}

/**
 * 이미지 픽셀을 비슷한 색끼리 묶어 대표색 후보를 만든다. 아주 적게 쓰인 색(잡티)은 뺀다.
 *
 * @param data - RGBA 픽셀 값
 * @returns 많이 쓰인 순서의 후보
 */
function toCandidates(data: Uint8ClampedArray): Candidate[] {
  const shift = 8 - IMAGE_PALETTE.binBits;
  // 묶음 번호 → [개수, R 합, G 합, B 합]
  const bins = new Map<number, [number, number, number, number]>();
  let total = 0;
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 128) continue; // 투명한 픽셀은 세지 않는다
    const [r, g, b] = [data[i], data[i + 1], data[i + 2]];
    const key =
      ((r >> shift) << (2 * IMAGE_PALETTE.binBits)) |
      ((g >> shift) << IMAGE_PALETTE.binBits) |
      (b >> shift);
    const bin = bins.get(key) ?? [0, 0, 0, 0];
    bin[0] += 1;
    bin[1] += r;
    bin[2] += g;
    bin[3] += b;
    bins.set(key, bin);
    total += 1;
  }
  return [...bins.values()]
    .filter(([count]) => count / total >= IMAGE_PALETTE.minShare)
    .sort((x, y) => y[0] - x[0])
    .map(([count, r, g, b]) => {
      const [ar, ag, ab] = [r / count, g / count, b / count];
      return { hex: toHex(ar, ag, ab), lab: toOklab(ar, ag, ab), share: count / total };
    });
}

/**
 * 후보 중에서 서로 최대한 다른 색을 고른다. 첫 색은 가장 많이 쓰인 색이고, 다음부터는
 * 이미 고른 색들과 가장 먼 색(밝기·색조·채도 모두 반영)을 고르되 많이 쓰인 색에 조금 가산점을 준다.
 * 그래서 비슷한 색조의 밝은 색만 몰려 나오지 않는다.
 *
 * @param candidates - 많이 쓰인 순서의 후보
 * @returns #RRGGBB 목록 (최대 IMAGE_PALETTE.size개)
 */
function pickDiverse(candidates: Candidate[]): string[] {
  if (candidates.length === 0) return [];
  const picked: Candidate[] = [candidates[0]];
  while (picked.length < IMAGE_PALETTE.size) {
    let best: Candidate | null = null;
    let bestScore = 0;
    for (const candidate of candidates) {
      const nearest = Math.min(...picked.map((p) => distance(candidate.lab, p.lab)));
      if (nearest < IMAGE_PALETTE.minDistance) continue;
      const score = nearest * candidate.share ** IMAGE_PALETTE.shareWeight;
      if (score > bestScore) {
        best = candidate;
        bestScore = score;
      }
    }
    if (!best) break;
    picked.push(best);
  }
  return picked.map((candidate) => candidate.hex);
}

/**
 * 이미지에서 서로 다른 대표색을 최대 IMAGE_PALETTE.size개 뽑는다.
 *
 * @param imageBase64 - PNG 이미지의 base64 문자열
 * @returns #RRGGBB 목록 (단순한 이미지는 더 적을 수 있다)
 * @throws {Error} 이미지를 읽지 못했을 때
 */
export async function extractPalette(imageBase64: string): Promise<string[]> {
  const image = new Image();
  image.src = `data:image/png;base64,${imageBase64}`;
  await image.decode();

  const scale = IMAGE_PALETTE.sampleSide / Math.max(image.naturalWidth, image.naturalHeight);
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
  canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
  const context = canvas.getContext("2d");
  if (!context) throw new Error("캔버스를 만들지 못했어요");
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  const { data } = context.getImageData(0, 0, canvas.width, canvas.height);
  return pickDiverse(toCandidates(data));
}

/** 이미지 → 뽑은 대표색. 이미지마다 한 번만 계산한다 */
const paletteCache = new WeakMap<GeneratedImage, Promise<string[]>>();

/**
 * 이미지의 대표색을 구한다. 처음에는 빈 목록이고, 계산이 끝나면 대표색으로 바뀐다.
 *
 * @param image - 생성된 이미지
 * @returns #RRGGBB 목록. 계산 중이거나 실패하면 빈 목록
 */
export function useImagePalette(image: GeneratedImage): string[] {
  const [palette, setPalette] = useState<string[]>([]);

  useEffect(() => {
    // 다른 이미지로 바뀐 뒤 늦게 끝난 계산은 무시한다
    let ignore = false;
    setPalette([]);
    let pending = paletteCache.get(image);
    if (!pending) {
      pending = extractPalette(image.image_base64);
      paletteCache.set(image, pending);
    }
    pending
      .then((colors) => {
        if (!ignore) setPalette(colors);
      })
      .catch((error) => console.error("대표색 계산 실패", error));
    return () => {
      ignore = true;
    };
  }, [image]);

  return palette;
}

/** 지금 편집 중인 이미지의 대표색. 에디터의 색 고르기 칸(ColorField)이 읽는다 */
export const ImagePaletteContext = createContext<string[]>([]);
