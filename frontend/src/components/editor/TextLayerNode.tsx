/**
 * 캔버스에 문구 상자 하나를 그리는 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
 * 수정자: bioyejin
 */

import { useLayoutEffect, useRef } from "react";
import type Konva from "konva";
import { Group, Rect, Text } from "react-konva";
import { resolveLayerFont, withAlpha, type TextLayer } from "./textLayer";

/** 문구 상자 묶음(Group)의 이름. 캔버스에서 누른 곳이 문구 상자인지 알아보는 데 쓴다 */
export const TEXT_LAYER_NODE_NAME = "text-layer";

/** 글자가 캔버스에서 차지하는 크기 (원본 이미지 px, 배경 상자 여백 제외) */
export interface TextLayerSize {
  width: number;
  height: number;
}

export interface TextLayerNodeProps {
  layer: TextLayer;
  /** 원본 이미지 크기(px). 비율로 저장된 위치·크기를 px로 바꾸는 데 쓴다 */
  imageWidth: number;
  imageHeight: number;
  /** 직접 입력 중이면 캔버스 글자는 숨기고 그 자리에 입력 칸을 띄운다 */
  editing: boolean;
  /** 그려진 Konva 노드를 등록·해제한다 (선택 테두리를 붙이는 데 사용) */
  onRegister: (id: string, node: Konva.Group | null) => void;
  /** 글자 크기가 정해질 때마다 알린다 (직접 입력 칸의 크기를 맞추는 데 사용) */
  onMeasure: (id: string, size: TextLayerSize) => void;
  onSelect: (id: string) => void;
  onStartEdit: (id: string) => void;
  /** 끌어서 옮긴 뒤 새 위치(비율)를 알린다 */
  onMove: (id: string, x: number, y: number) => void;
  /** 핸들로 크기·각도를 바꾼 뒤 배율, 새 위치(비율), 각도를 알린다 */
  onTransform: (id: string, ratio: number, x: number, y: number, rotation: number) => void;
  /** 끌기·크기 조절·회전을 시작하면 true, 끝나면 false (그동안 상자 위 도구줄을 숨긴다) */
  onInteract: (active: boolean) => void;
}

/**
 * 문구 상자 하나를 그린다. 묶음(Group)이 상자 가운데에 놓여 위치·회전·투명도를 맡고,
 * 그 안의 배경 상자와 글자는 묶음 가운데를 기준으로 맞춘다.
 * 클릭하면 선택, 더블클릭하면 직접 입력, 끌면 이동한다. 가운데가 이미지 밖으로 나가지 않는다.
 * 끌기로 생긴 위치와 핸들로 생긴 배율·각도는 끝날 때 데이터에 옮겨 담는다.
 *
 * @param props - 문구 상자, 이미지 크기, 입력 중 여부와 처리 함수
 * @returns Konva Group 노드
 */
export default function TextLayerNode({
  layer,
  imageWidth,
  imageHeight,
  editing,
  onRegister,
  onMeasure,
  onSelect,
  onStartEdit,
  onMove,
  onTransform,
  onInteract,
}: TextLayerNodeProps) {
  const groupRef = useRef<Konva.Group>(null);
  const textRef = useRef<Konva.Text>(null);
  const backgroundRef = useRef<Konva.Rect>(null);
  const backgroundPadding = (layer.background?.padding ?? 0) * imageHeight;
  const font = resolveLayerFont(layer);
  const { id } = layer;

  useLayoutEffect(() => {
    onRegister(id, groupRef.current);
    return () => onRegister(id, null);
  }, [id, onRegister]);

  // 문구·글꼴·크기가 바뀔 때마다 그려진 크기를 다시 재서 글자와 배경 상자를 가운데에 맞춘다
  useLayoutEffect(() => {
    const text = textRef.current;
    if (!text) return;
    const width = text.width();
    const height = text.height();
    text.offsetX(width / 2);
    text.offsetY(height / 2);
    backgroundRef.current?.setAttrs({
      x: -width / 2 - backgroundPadding,
      y: -height / 2 - backgroundPadding,
      width: width + backgroundPadding * 2,
      height: height + backgroundPadding * 2,
    });
    onMeasure(id, { width, height });
  });

  return (
    <Group
      ref={groupRef}
      name={TEXT_LAYER_NODE_NAME}
      x={layer.x * imageWidth}
      y={layer.y * imageHeight}
      rotation={layer.rotation}
      opacity={layer.opacity}
      draggable={!editing}
      onMouseDown={() => onSelect(id)}
      onTouchStart={() => onSelect(id)}
      onDblClick={() => onStartEdit(id)}
      onDblTap={() => onStartEdit(id)}
      onDragStart={() => onInteract(true)}
      onDragMove={(e) => {
        const node = e.target;
        node.x(Math.min(imageWidth, Math.max(0, node.x())));
        node.y(Math.min(imageHeight, Math.max(0, node.y())));
      }}
      onDragEnd={(e) => {
        onMove(id, e.target.x() / imageWidth, e.target.y() / imageHeight);
        onInteract(false);
      }}
      onTransformStart={() => onInteract(true)}
      onTransformEnd={(e) => {
        // 핸들은 노드 배율만 바꾸므로, 글자 크기에 옮겨 담고 배율은 되돌린다
        const node = e.target;
        const ratio = node.scaleX();
        node.scaleX(1);
        node.scaleY(1);
        onTransform(id, ratio, node.x() / imageWidth, node.y() / imageHeight, node.rotation());
        onInteract(false);
      }}
    >
      {layer.background && (
        <Rect
          ref={backgroundRef}
          fill={layer.background.color}
          opacity={layer.background.opacity}
          cornerRadius={layer.background.radius * imageHeight}
        />
      )}
      <Text
        ref={textRef}
        text={layer.text}
        width={layer.width === null ? undefined : layer.width * imageWidth}
        fontFamily={font.family}
        fontSize={layer.fontSize * imageHeight}
        fontStyle={`${font.italic ? "italic " : ""}${font.weight}`}
        textDecoration={layer.strike ? "line-through" : ""}
        align={layer.align}
        lineHeight={layer.lineHeight}
        wrap="word"
        fill={layer.color}
        stroke={layer.stroke ? withAlpha(layer.stroke.color, layer.stroke.opacity) : undefined}
        strokeWidth={layer.stroke ? layer.stroke.width * imageHeight : 0}
        lineJoin={layer.stroke?.join}
        // 외곽선을 글자 뒤에 그려 글자가 가늘어지지 않게 한다
        fillAfterStrokeEnabled
        shadowEnabled={layer.shadow !== null}
        shadowColor={layer.shadow?.color}
        shadowBlur={(layer.shadow?.blur ?? 0) * imageHeight}
        shadowOffsetX={(layer.shadow?.offsetX ?? 0) * imageHeight}
        shadowOffsetY={(layer.shadow?.offsetY ?? 0) * imageHeight}
        shadowOpacity={layer.shadow?.opacity ?? 0}
        visible={!editing}
      />
    </Group>
  );
}
