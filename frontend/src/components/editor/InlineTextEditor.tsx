/**
 * 캔버스 위 문구 상자 자리에서 글자를 바로 입력하는 칸.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
 * 수정자: bioyejin
 */

import { useEffect, useRef } from "react";
import { DEFAULT_LAYER_TEXT } from "../../constants/editor";
import { resolveLayerFont, withAlpha, type TextLayer } from "./textLayer";
import type { TextLayerSize } from "./TextLayerNode";
import styles from "./InlineTextEditor.module.css";

/**
 * 그림자 값을 CSS text-shadow 값으로 바꾼다.
 *
 * @param shadow - 그림자 값 (없으면 null)
 * @param heightPx - 화면에 보이는 이미지 세로(px)
 * @returns CSS 값. 그림자가 없으면 "none"
 */
function toCssTextShadow(shadow: TextLayer["shadow"], heightPx: number): string {
  if (!shadow) return "none";
  const { offsetX, offsetY, blur, color, opacity } = shadow;
  const offset = `${offsetX * heightPx}px ${offsetY * heightPx}px`;
  return `${offset} ${blur * heightPx}px ${withAlpha(color, opacity)}`;
}

export interface InlineTextEditorProps {
  layer: TextLayer;
  /** 캔버스에 그려진 문구 크기 (원본 이미지 px). 입력할 때마다 캔버스가 다시 재서 알려준다 */
  size: TextLayerSize | undefined;
  imageWidth: number;
  imageHeight: number;
  /** 원본 이미지 px → 화면 px 배율 */
  scale: number;
  onChange: (text: string) => void;
  /** 바깥을 누르거나 Esc를 누르면 호출 */
  onDone: () => void;
}

/**
 * 캔버스 글자와 같은 위치·글꼴·크기의 입력 칸(textarea)을 겹쳐 띄워 바로 입력하게 한다.
 * 한글 조합 입력이 안정적이도록 캔버스가 아닌 일반 입력 칸을 쓴다.
 * Enter는 줄바꿈이고, Esc나 바깥 클릭으로 입력을 끝낸다. 새 상자의 기본 문구는 전체 선택해 바로 덮어쓰게 한다.
 *
 * @param props - 문구 상자, 그려진 크기, 이미지 크기, 배율, 입력·종료 처리 함수
 * @returns 입력 칸
 */
export default function InlineTextEditor({
  layer,
  size,
  imageWidth,
  imageHeight,
  scale,
  onChange,
  onDone,
}: InlineTextEditorProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const font = resolveLayerFont(layer);
  const fontSizePx = layer.fontSize * imageHeight * scale;

  // 열릴 때 한 번만 포커스한다 (입력 중에 다시 선택되면 안 되므로 문구는 의존성에서 뺀다)
  useEffect(() => {
    const textarea = ref.current;
    if (!textarea) return;
    textarea.focus();
    if (textarea.value === DEFAULT_LAYER_TEXT) textarea.select();
    else textarea.setSelectionRange(textarea.value.length, textarea.value.length);
  }, [layer.id]);

  // 캔버스가 잰 크기에 맞춘다. 폭이 자동이면 커서가 들어갈 여유를 조금 더 준다
  const autoWidth = layer.width === null;
  const width = autoWidth
    ? (size?.width ?? 0) * scale + fontSizePx * 0.5
    : (layer.width ?? 0) * imageWidth * scale;
  const height = Math.max(size?.height ?? 0, layer.fontSize * imageHeight * layer.lineHeight);

  return (
    <textarea
      ref={ref}
      className={`${styles.input} ${autoWidth ? styles.autoWidth : ""}`}
      value={layer.text}
      aria-label="문구 입력"
      spellCheck={false}
      style={{
        left: layer.x * imageWidth * scale,
        top: layer.y * imageHeight * scale,
        width: Math.max(width, fontSizePx),
        height: height * scale,
        transform: `translate(-50%, -50%) rotate(${layer.rotation}deg)`,
        fontFamily: font.family,
        fontSize: fontSizePx,
        fontWeight: font.weight,
        fontStyle: font.italic ? "italic" : "normal",
        textDecoration: layer.strike ? "line-through" : "none",
        textAlign: layer.align,
        lineHeight: layer.lineHeight,
        color: layer.color,
        opacity: layer.opacity,
        // 캔버스처럼 외곽선을 글자 뒤에 그린다
        WebkitTextStroke: layer.stroke
          ? `${layer.stroke.width * imageHeight * scale}px ${withAlpha(layer.stroke.color, layer.stroke.opacity)}`
          : undefined,
        paintOrder: "stroke fill",
        textShadow: toCssTextShadow(layer.shadow, imageHeight * scale),
      }}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onDone}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          ref.current?.blur();
        }
      }}
    />
  );
}
