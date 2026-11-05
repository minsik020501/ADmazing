/**
 * 문구 상자(텍스트 레이어) 데이터 형식과 값 검사.
 *
 * 에디터 화면은 이 데이터를 그리기만 한다. 사용자가 직접 넣은 문구와, 나중에 모델이 추천해 보낼
 * 문구(JSON)가 같은 형식이므로 추천 결과는 normalizeTextLayers로 검사한 뒤 그대로 쓸 수 있다.
 * 형식 설명: docs/text_layer_spec.md
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

import {
  DEFAULT_FONT_ID,
  DEFAULT_FONT_SIZE,
  DEFAULT_LAYER_TEXT,
  LAYER_LIMITS,
} from "../../constants/editor";
import { AD_FONTS, toFontFamily, type AdFont } from "../../constants/fonts";

/** 여러 줄 문구의 줄 맞춤 */
export type TextAlign = "left" | "center" | "right";

/** 글자 외곽선 */
export interface TextStroke {
  color: string;
  /** 두께 (이미지 세로 대비 비율) */
  width: number;
}

/** 글자 그림자 */
export interface TextShadow {
  color: string;
  /** 흐림 정도 (이미지 세로 대비 비율) */
  blur: number;
  /** 그림자 위치 (이미지 세로 대비 비율, 오른쪽·아래가 +) */
  offsetX: number;
  offsetY: number;
  /** 0~1 */
  opacity: number;
}

/**
 * 문구 상자 하나. 위치·크기는 픽셀이 아니라 이미지 대비 비율이라 해상도·화면 크기와 상관없다.
 * 볼드·외곽선·회전 같은 값은 화면 기능이 아직 없어도 형식에는 미리 둔다.
 */
export interface TextLayer {
  id: string;
  /** 문구의 역할 (예: headline, body). 초기 화면의 문구 요청과 짝을 맞출 때 쓴다 */
  role: string | null;
  text: string;
  /** 상자 가운데 위치 (이미지 가로·세로 대비 비율, 0~1) */
  x: number;
  y: number;
  /** 줄바꿈 폭 (이미지 가로 대비 비율). null이면 문구 길이만큼 넓어지고 Enter로만 줄을 바꾼다 */
  width: number | null;
  /** 회전 (도, 시계 방향이 +) */
  rotation: number;
  /** 구부리기 (-100~100, 0이면 직선) */
  curve: number;
  /** 글꼴 id (constants/fonts.ts) */
  fontId: string;
  /** 글자 크기 (이미지 세로 대비 비율) */
  fontSize: number;
  bold: boolean;
  italic: boolean;
  strike: boolean;
  align: TextAlign;
  /** 글자색 (#RRGGBB) */
  color: string;
  /** 투명도 (0~1, 1이면 불투명) */
  opacity: number;
  stroke: TextStroke | null;
  shadow: TextShadow | null;
}

const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;
const ALIGNS: TextAlign[] = ["left", "center", "right"];
const MAX_ROLE_LENGTH = 30;

// 문구 상자 id에 붙이는 번호 (같은 시각에 여러 개를 만들어도 겹치지 않게)
let idCounter = 0;

/**
 * 겹치지 않는 문구 상자 id를 만든다.
 * (crypto.randomUUID는 https·localhost에서만 동작해 IP로 접속하는 서버에서는 쓰지 않는다)
 *
 * @returns 새 id
 */
function createLayerId(): string {
  idCounter += 1;
  return `layer-${Date.now().toString(36)}-${idCounter}`;
}

/**
 * 기본값으로 채운 새 문구 상자를 만든다.
 *
 * @param overrides - 기본값 대신 쓸 값
 * @returns 새 문구 상자
 */
export function createTextLayer(overrides: Partial<Omit<TextLayer, "id">> = {}): TextLayer {
  return {
    role: null,
    text: DEFAULT_LAYER_TEXT,
    x: 0.5,
    y: 0.5,
    width: null,
    rotation: 0,
    curve: 0,
    fontId: DEFAULT_FONT_ID,
    fontSize: DEFAULT_FONT_SIZE,
    bold: false,
    italic: false,
    strike: false,
    align: "center",
    color: "#FFFFFF",
    opacity: 1,
    stroke: null,
    shadow: null,
    ...overrides,
    id: createLayerId(),
  };
}

/**
 * 글꼴 id로 글꼴 정보를 찾는다. 모르는 id면 기본 글꼴을 돌려준다.
 *
 * @param fontId - 글꼴 id
 * @returns 글꼴 정보
 */
export function findFont(fontId: string): AdFont {
  return (
    AD_FONTS.find((font) => font.id === fontId) ??
    AD_FONTS.find((font) => font.id === DEFAULT_FONT_ID) ??
    AD_FONTS[0]
  );
}

/**
 * 글꼴에 준비된 굵기 중 실제로 쓸 굵기를 고른다.
 * 보통은 400에 가장 가까운 굵기, 볼드는 준비된 굵기 중 가장 두꺼운 것(600 미만이면 브라우저가 두껍게 그림).
 *
 * @param font - 글꼴 정보
 * @param bold - 볼드 여부
 * @returns CSS font-weight 값
 */
export function resolveFontWeight(font: AdFont, bold: boolean): number {
  if (font.weights.length === 0) return bold ? 700 : 400;
  if (bold) return Math.max(Math.max(...font.weights), 700);
  // 거리가 같으면(예: 300과 500) 더 두꺼운 쪽을 쓴다 (브라우저가 400을 찾을 때와 같은 순서)
  return font.weights.reduce((best, weight) => {
    const distance = Math.abs(weight - 400);
    const bestDistance = Math.abs(best - 400);
    return distance < bestDistance || (distance === bestDistance && weight > best) ? weight : best;
  });
}

/** 문구 상자를 그릴 때 쓰는 글꼴 정보 */
export interface ResolvedFont {
  /** CSS font-family 값 (기본 글꼴 포함) */
  family: string;
  weight: number;
  italic: boolean;
}

/**
 * 문구 상자의 글꼴 id·볼드·이탤릭을 실제로 그릴 글꼴 정보로 바꾼다.
 *
 * @param layer - 문구 상자
 * @returns 글꼴 이름, 굵기, 기울임
 */
export function resolveLayerFont(layer: TextLayer): ResolvedFont {
  const font = findFont(layer.fontId);
  return {
    family: toFontFamily(font),
    weight: resolveFontWeight(font, layer.bold),
    italic: layer.italic,
  };
}

/**
 * CSS font 값을 만든다. 글꼴 미리 받기(document.fonts.load)에 쓴다.
 *
 * @param font - 글꼴 정보
 * @param sizePx - 글자 크기(px)
 * @returns 예: `italic 700 32px "Pretendard", sans-serif`
 */
export function toCssFont(font: ResolvedFont, sizePx: number): string {
  return `${font.italic ? "italic " : ""}${font.weight} ${sizePx}px ${font.family}`;
}

/** 숫자면 범위 안으로 맞추고, 숫자가 아니면 기본값을 쓴다. */
function toNumber(value: unknown, fallback: number, min: number, max: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, value));
}

/** #RRGGBB 형식의 색이면 대문자로, 아니면 기본값을 쓴다. */
function toColor(value: unknown, fallback: string): string {
  return typeof value === "string" && HEX_COLOR.test(value) ? value.toUpperCase() : fallback;
}

/** 객체인지 확인한다. */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** 외곽선 값을 검사한다. 없거나 형식이 틀리면 null. */
function toStroke(value: unknown): TextStroke | null {
  if (!isRecord(value)) return null;
  const { min, max } = LAYER_LIMITS.strokeWidth;
  return { color: toColor(value.color, "#000000"), width: toNumber(value.width, 0.004, min, max) };
}

/** 그림자 값을 검사한다. 없거나 형식이 틀리면 null. */
function toShadow(value: unknown): TextShadow | null {
  if (!isRecord(value)) return null;
  const blur = LAYER_LIMITS.shadowBlur;
  const offset = LAYER_LIMITS.shadowOffset;
  return {
    color: toColor(value.color, "#000000"),
    blur: toNumber(value.blur, 0.01, blur.min, blur.max),
    offsetX: toNumber(value.offsetX, 0.003, offset.min, offset.max),
    offsetY: toNumber(value.offsetY, 0.003, offset.min, offset.max),
    opacity: toNumber(value.opacity, 0.5, 0, 1),
  };
}

/**
 * 밖에서 받은 문구 상자 하나(모델 추천 JSON 등)를 검사해 에디터가 쓸 수 있는 값으로 맞춘다.
 * 범위 밖 숫자는 범위 안으로, 모르는 글꼴은 기본 글꼴로, 빠진 값은 기본값으로 채운다.
 * id는 항상 새로 만든다.
 *
 * @param raw - 검사할 값
 * @returns 문구 상자. 문구가 비었거나 객체가 아니면 null
 */
export function normalizeTextLayer(raw: unknown): TextLayer | null {
  if (!isRecord(raw) || typeof raw.text !== "string") return null;
  const text = raw.text.slice(0, LAYER_LIMITS.textLength.max);
  if (text.trim() === "") return null;

  const limits = LAYER_LIMITS;
  const defaults = createTextLayer();
  return {
    ...defaults,
    role:
      typeof raw.role === "string" && raw.role.trim() !== ""
        ? raw.role.trim().slice(0, MAX_ROLE_LENGTH)
        : null,
    text,
    x: toNumber(raw.x, defaults.x, 0, 1),
    y: toNumber(raw.y, defaults.y, 0, 1),
    width:
      raw.width === null || raw.width === undefined
        ? null
        : toNumber(raw.width, limits.width.max, limits.width.min, limits.width.max),
    rotation: toNumber(raw.rotation, 0, limits.rotation.min, limits.rotation.max),
    curve: toNumber(raw.curve, 0, limits.curve.min, limits.curve.max),
    fontId: typeof raw.fontId === "string" ? findFont(raw.fontId).id : defaults.fontId,
    fontSize: toNumber(raw.fontSize, defaults.fontSize, limits.fontSize.min, limits.fontSize.max),
    bold: raw.bold === true,
    italic: raw.italic === true,
    strike: raw.strike === true,
    align: ALIGNS.includes(raw.align as TextAlign) ? (raw.align as TextAlign) : defaults.align,
    color: toColor(raw.color, defaults.color),
    opacity: toNumber(raw.opacity, 1, 0, 1),
    stroke: toStroke(raw.stroke),
    shadow: toShadow(raw.shadow),
  };
}

/**
 * 밖에서 받은 문구 상자 목록을 검사한다. 쓸 수 없는 항목은 빼고, 개수가 많으면 앞에서부터 자른다.
 *
 * @param raw - 검사할 값 (배열이 아니면 빈 목록)
 * @returns 문구 상자 목록
 */
export function normalizeTextLayers(raw: unknown): TextLayer[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map(normalizeTextLayer)
    .filter((layer): layer is TextLayer => layer !== null)
    .slice(0, LAYER_LIMITS.layerCount.max);
}
