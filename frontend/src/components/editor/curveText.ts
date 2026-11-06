/**
 * 문구를 곡선 위에 그리기 위한 계산.
 *
 * 생성일자: 2026-11-06
 * 생성자: bioyejin
 * 수정일자: 2026-11-06
 * 수정자: bioyejin
 */

import type Konva from "konva";
import type { Context } from "konva/lib/Context";
import type { Shape } from "konva/lib/Shape";
import { getDecorationLineWidth } from "konva/lib/shapes/Text";
import { LAYER_LIMITS } from "../../constants/editor";
import type { TextLayer } from "./textLayer";

// 구부리기가 최대일 때 곡선이 그리는 각도 (라디안). 반원
const MAX_SWEEP = Math.PI;
// 곡선이 글자 폭보다 조금 길어야 계산 오차로 마지막 글자가 잘리지 않는다
const PATH_SLACK_RATIO = 0.02;
// 반투명한 외곽선을 한 덩어리로 그릴 때 쓰는 임시 캔버스 (그릴 때마다 만들지 않고 재사용)
let mergedStrokeCanvas: HTMLCanvasElement | null = null;

/**
 * 구부릴 수 있는 문구인지 확인한다. 곡선 하나에 한 줄만 올릴 수 있다.
 *
 * @param text - 문구
 * @returns 한 줄이면 true
 */
export function canCurve(text: string): boolean {
  return !text.includes("\n");
}

/**
 * 곡선으로 그려야 하는 문구 상자인지 확인한다.
 *
 * @param layer - 문구 상자
 * @returns 구부리기 값이 있고 한 줄이면 true
 */
export function isCurved(layer: TextLayer): boolean {
  return layer.curve !== 0 && canCurve(layer.text);
}

/**
 * 문구를 올릴 원호를 SVG path 문자열로 만든다. 호의 길이를 글자 폭에 맞춰 글자 간격이 유지되고,
 * 양 끝과 가장 높은 곳의 가운데가 (0, 0)에 오도록 위아래로 맞춘다.
 *
 * @param textWidth - 직선일 때 글자 폭 (px)
 * @param curve - 구부리기 값. 양수면 위로 볼록, 음수면 아래로 볼록 (0은 안 됨)
 * @returns SVG path 문자열
 */
export function toCurvePath(textWidth: number, curve: number): string {
  const length = textWidth * (1 + PATH_SLACK_RATIO);
  const sweep = (Math.abs(curve) / LAYER_LIMITS.curve.max) * MAX_SWEEP;
  const radius = length / sweep;
  const halfChord = (radius * Math.sin(sweep / 2)).toFixed(3);
  const rise = radius * (1 - Math.cos(sweep / 2));
  const y = ((curve > 0 ? rise : -rise) / 2).toFixed(3);
  const r = radius.toFixed(3);
  // 왼쪽에서 오른쪽으로 그릴 때 시계 방향(1)이면 위로, 반시계 방향(0)이면 아래로 볼록하다
  return `M -${halfChord} ${y} A ${r} ${r} 0 0 ${curve > 0 ? 1 : 0} ${halfChord} ${y}`;
}

/**
 * 반투명한 외곽선을 그린다. 글자별로 반투명하게 그리면 겹친 곳만 진해지므로, 불투명하게 한 덩어리로
 * 그린 뒤 투명도를 한 번만 입힌다.
 *
 * @param context - 그릴 곳
 * @param path - TextPath 노드
 * @param opacity - 외곽선 불투명도 (0~1)
 */
function drawTranslucentStroke(context: Context, path: Konva.TextPath, opacity: number) {
  const target = context._context;
  const { width, height } = target.canvas;
  mergedStrokeCanvas ??= document.createElement("canvas");
  if (mergedStrokeCanvas.width !== width) mergedStrokeCanvas.width = width;
  if (mergedStrokeCanvas.height !== height) mergedStrokeCanvas.height = height;
  const merged = mergedStrokeCanvas.getContext("2d");
  if (!merged) return;

  merged.setTransform(1, 0, 0, 1, 0, 0);
  merged.clearRect(0, 0, width, height);
  merged.setTransform(target.getTransform());
  merged.font = target.font;
  merged.textBaseline = target.textBaseline;
  merged.textAlign = target.textAlign;
  merged.lineJoin = target.lineJoin;
  merged.miterLimit = target.miterLimit;
  merged.lineWidth = path.strokeWidth();
  merged.strokeStyle = path.stroke() as string;
  for (const glyph of path.glyphInfo) {
    merged.save();
    merged.translate(glyph.p0.x, glyph.p0.y);
    merged.rotate(glyph.rotation);
    merged.strokeText(glyph.text, 0, 0);
    merged.restore();
  }

  // 임시 캔버스는 이미 최종 위치에 그려져 있으므로 변환 없이 그대로 얹는다
  target.save();
  target.setTransform(1, 0, 0, 1, 0, 0);
  target.globalAlpha *= opacity;
  target.drawImage(mergedStrokeCanvas, 0, 0);
  target.restore();
}

/**
 * 곡선 문구를 그린다. Konva의 TextPath는 글자마다 외곽선과 채우기를 함께 그려서 다음 글자의
 * 외곽선이 앞 글자를 덮는다. 그래서 모든 글자의 외곽선을 먼저 그리고 그 위에 글자를 채운다.
 *
 * @param context - 그릴 곳
 * @param shape - TextPath 노드. 외곽선 색은 불투명하게, 불투명도는 strokeOpacity 속성으로 받는다
 */
export function drawCurvedText(context: Context, shape: Shape) {
  const path = shape as Konva.TextPath;
  const glyphs = path.glyphInfo;
  const strokeOpacity: number = path.getAttr("strokeOpacity") ?? 1;

  /** 글자마다 그 글자의 위치와 각도로 옮겨 그린다. */
  function drawGlyphs(draw: (glyph: (typeof glyphs)[number], index: number) => void) {
    glyphs.forEach((glyph, index) => {
      context.save();
      context.translate(glyph.p0.x, glyph.p0.y);
      context.rotate(glyph.rotation);
      path.partialText = glyph.text;
      draw(glyph, index);
      context.restore();
    });
  }

  context.setAttr("font", path._getContextFont());
  context.setAttr("textBaseline", path.textBaseline());
  context.setAttr("textAlign", "left");
  if (path.hasStroke() && strokeOpacity < 1) drawTranslucentStroke(context, path, strokeOpacity);
  else drawGlyphs(() => context.strokeShape(path));
  drawGlyphs(() => context.fillShape(path));

  if (path.textDecoration().includes("line-through")) {
    context.beginPath();
    drawGlyphs((glyph, index) => {
      if (index === 0) context.moveTo(0, 0);
      context.lineTo(glyph.width, 0);
    });
    context.setAttr("strokeStyle", path.fill());
    context.setAttr("lineWidth", getDecorationLineWidth(path.fontSize()));
    context.stroke();
  }
}
