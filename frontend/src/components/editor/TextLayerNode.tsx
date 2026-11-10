/**
 * 캔버스에 문구 상자 하나를 그리는 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { useLayoutEffect, useRef } from "react";
import type Konva from "konva";
import type { Context } from "konva/lib/Context";
import type { Shape } from "konva/lib/Shape";
import { Group, Rect, Text, TextPath } from "react-konva";
import { SELECTION_PADDING_PX } from "../../constants/editor";
import { drawCurvedText, isCurved, toCurvePath } from "./curveText";
import { resolveLayerFont, withAlpha, type TextLayer } from "./textLayer";

/** 문구 상자 묶음(Group)의 이름. 캔버스에서 누른 곳이 문구 상자인지 알아보는 데 쓴다 */
export const TEXT_LAYER_NODE_NAME = "text-layer";

/** 여러 개 선택했을 때 상자마다 그리는 선택 테두리의 이름. 편집본을 저장할 때 숨기는 데 쓴다 */
export const SELECTION_OUTLINE_NAME = "selection-outline";

// 여러 개 선택 테두리 두께 (화면 px). 하나만 선택했을 때의 테두리(Transformer)와 같게 맞춘다
const OUTLINE_WIDTH_PX = 1.5;

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
  /**
   * 여러 개 선택 중이면 상자 안에 선택 테두리를 그린다. 이때는 Transformer를 붙이지 않아
   * 함께 끌기를 캔버스(onSnap)가 맡고, 테두리는 상자와 함께 움직인다
   */
  outlineColor: string | null;
  /** 그려진 Konva 노드를 등록·해제한다 (선택 테두리를 붙이는 데 사용) */
  onRegister: (id: string, node: Konva.Group | null) => void;
  /** 글자 크기가 정해질 때마다 알린다 (직접 입력 칸의 크기를 맞추는 데 사용) */
  onMeasure: (id: string, size: TextLayerSize) => void;
  /**
   * 상자를 누를 때 호출. additive는 Ctrl(맥은 ⌘)을 누른 채 눌렀는지로, 선택에 더하거나 뺀다.
   * 끌기 전에 불리므로, 이미 선택된 상자를 누르면 여러 개 선택을 그대로 둔다(함께 끌기)
   */
  onPress: (id: string, additive: boolean) => void;
  /** 끌지 않고 클릭으로 끝났을 때 호출 (Ctrl 없이 클릭하면 그 상자 하나만 선택한다) */
  onClick: (id: string, additive: boolean) => void;
  onStartEdit: (id: string) => void;
  /** 끌어서 옮긴 뒤 새 위치(비율)를 알린다 */
  onMove: (id: string, x: number, y: number) => void;
  /** 핸들로 크기·각도를 바꾼 뒤 배율, 새 위치(비율), 각도를 알린다 */
  onTransform: (id: string, ratio: number, x: number, y: number, rotation: number) => void;
  /**
   * 끄는 동안 지금 위치(원본 px)를 넘기면, 캔버스 가운데선과 다른 상자에 맞춘 위치를 돌려준다
   * (안내선도 그쪽에서 그린다)
   */
  onSnap: (id: string, x: number, y: number) => { x: number; y: number };
  /** 끌기가 끝나 안내선을 지울 때 호출 */
  onSnapEnd: () => void;
  /** 끌기·크기 조절·회전을 시작하면 true, 끝나면 false (그동안 상자 위 도구줄을 숨긴다) */
  onInteract: (active: boolean) => void;
}

/**
 * 잡을 수 있는 영역을 그린다. 선택 테두리까지 잡히도록 상자보다 넓지만, 화면에는 보이지 않고
 * 선택 테두리 계산에도 들어가지 않는다.
 *
 * @param context - 그릴 곳
 * @param shape - 상자 크기의 투명한 사각형
 */
function drawHitArea(context: Context, shape: Shape) {
  const padding = SELECTION_PADDING_PX / (shape.getStage()?.scaleX() || 1);
  context.beginPath();
  context.rect(-padding, -padding, shape.width() + padding * 2, shape.height() + padding * 2);
  context.closePath();
  context.fillStrokeShape(shape);
}

/**
 * 문구 상자 하나를 그린다. 묶음(Group)이 상자 가운데에 놓여 위치·회전·투명도를 맡고,
 * 그 안의 배경 상자와 글자는 묶음 가운데를 기준으로 맞춘다. 구부린 문구는 곡선 위에 그리고,
 * 직접 입력하는 동안에는 입력 칸과 맞도록 직선으로 돌아간다.
 * 글자 사이의 빈 곳을 포함해 상자 어디를 눌러도 클릭하면 선택, 더블클릭하면 직접 입력, 끌면 이동한다. 가운데가 이미지 밖으로 나가지 않고,
 * 캔버스 가운데선이나 다른 상자의 모서리·가운데 가까이에서는 달라붙는다(onSnap).
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
  outlineColor,
  onRegister,
  onMeasure,
  onPress,
  onClick,
  onStartEdit,
  onMove,
  onTransform,
  onSnap,
  onSnapEnd,
  onInteract,
}: TextLayerNodeProps) {
  const groupRef = useRef<Konva.Group>(null);
  const textRef = useRef<Konva.Text>(null);
  const pathRef = useRef<Konva.TextPath>(null);
  const backgroundRef = useRef<Konva.Rect>(null);
  const hitAreaRef = useRef<Konva.Rect>(null);
  const outlineRef = useRef<Konva.Rect>(null);
  const backgroundPadding = (layer.background?.padding ?? 0) * imageHeight;
  const font = resolveLayerFont(layer);
  const curved = isCurved(layer) && !editing;
  const { id } = layer;

  useLayoutEffect(() => {
    onRegister(id, groupRef.current);
    return () => onRegister(id, null);
  }, [id, onRegister]);

  // 문구·글꼴·크기가 바뀔 때마다 그려진 크기를 다시 재서 글자와 배경 상자를 가운데에 맞춘다
  useLayoutEffect(() => {
    const text = textRef.current;
    const path = pathRef.current;
    // 곡선 길이는 그려진 글자 폭으로 정하므로, 글자 폭을 잰 뒤에 곡선을 넣는다
    path?.data(toCurvePath(path.getTextWidth(), layer.curve));
    const node = path ?? text;
    if (!node) return;
    const { x, y, width, height } = path
      ? path.getSelfRect()
      : { x: 0, y: 0, width: node.width(), height: node.height() };
    node.offsetX(x + width / 2);
    node.offsetY(y + height / 2);
    const box = {
      x: -width / 2 - backgroundPadding,
      y: -height / 2 - backgroundPadding,
      width: width + backgroundPadding * 2,
      height: height + backgroundPadding * 2,
    };
    backgroundRef.current?.setAttrs(box);
    hitAreaRef.current?.setAttrs(box);
    // 여러 개 선택 테두리는 하나만 선택했을 때(Transformer)와 같은 여백·두께로 보이게 배율로 나눈다
    const scale = groupRef.current?.getStage()?.scaleX() || 1;
    const padding = SELECTION_PADDING_PX / scale;
    outlineRef.current?.setAttrs({
      x: box.x - padding,
      y: box.y - padding,
      width: box.width + padding * 2,
      height: box.height + padding * 2,
      strokeWidth: OUTLINE_WIDTH_PX / scale,
    });
    onMeasure(id, { width, height });
  });

  // 직선과 곡선이 함께 쓰는 글자 모양
  const textStyle = {
    text: layer.text,
    fontFamily: font.family,
    fontSize: layer.fontSize * imageHeight,
    fontStyle: `${font.italic ? "italic " : ""}${font.weight}`,
    textDecoration: layer.strike ? "line-through" : "",
    fill: layer.color,
    stroke: layer.stroke ? withAlpha(layer.stroke.color, layer.stroke.opacity) : undefined,
    strokeWidth: layer.stroke ? layer.stroke.width * imageHeight : 0,
    lineJoin: layer.stroke?.join,
    // 외곽선을 글자 뒤에 그려 글자가 가늘어지지 않게 한다
    fillAfterStrokeEnabled: true,
    shadowEnabled: layer.shadow !== null,
    shadowColor: layer.shadow?.color,
    shadowBlur: (layer.shadow?.blur ?? 0) * imageHeight,
    shadowOffsetX: (layer.shadow?.offsetX ?? 0) * imageHeight,
    shadowOffsetY: (layer.shadow?.offsetY ?? 0) * imageHeight,
    shadowOpacity: layer.shadow?.opacity ?? 0,
  };

  return (
    <Group
      ref={groupRef}
      name={TEXT_LAYER_NODE_NAME}
      x={layer.x * imageWidth}
      y={layer.y * imageHeight}
      rotation={layer.rotation}
      opacity={layer.opacity}
      draggable={!editing}
      onMouseDown={(e) => onPress(id, e.evt.ctrlKey || e.evt.metaKey)}
      onTouchStart={() => onPress(id, false)}
      // Konva는 끌기가 일어나면 click을 보내지 않는다
      onClick={(e) => onClick(id, e.evt.ctrlKey || e.evt.metaKey)}
      onTap={() => onClick(id, false)}
      onDblClick={() => onStartEdit(id)}
      onDblTap={() => onStartEdit(id)}
      onDragStart={() => onInteract(true)}
      onDragMove={(e) => {
        const node = e.target;
        node.position(onSnap(id, node.x(), node.y()));
      }}
      onDragEnd={(e) => {
        onSnapEnd();
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
      <Rect ref={hitAreaRef} fill="transparent" hitFunc={drawHitArea} />
      {layer.background && (
        <Rect
          ref={backgroundRef}
          fill={layer.background.color}
          opacity={layer.background.opacity}
          cornerRadius={layer.background.radius * imageHeight}
        />
      )}
      {curved ? (
        // 곡선 경로는 글자 폭을 잰 뒤에 위 useLayoutEffect에서 넣는다
        <TextPath
          ref={pathRef}
          {...textStyle}
          // 겹친 외곽선이 진해지지 않도록 불투명도는 drawCurvedText가 한 번만 입힌다
          stroke={layer.stroke?.color}
          strokeOpacity={layer.stroke?.opacity}
          align="center"
          sceneFunc={drawCurvedText}
        />
      ) : (
        <Text
          ref={textRef}
          {...textStyle}
          width={layer.width === null ? undefined : layer.width * imageWidth}
          align={layer.align}
          lineHeight={layer.lineHeight}
          wrap="word"
          visible={!editing}
        />
      )}
      {outlineColor && (
        <Rect
          ref={outlineRef}
          name={SELECTION_OUTLINE_NAME}
          stroke={outlineColor}
          listening={false}
        />
      )}
    </Group>
  );
}
