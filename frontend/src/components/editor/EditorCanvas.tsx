/**
 * 이미지와 문구 상자를 그리는 편집 영역(캔버스) 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-11
 * 수정자: bioyejin
 */

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import type Konva from "konva";
import { Image as KonvaImage, Layer, Line, Stage, Transformer } from "react-konva";
import {
  LAYER_LIMITS,
  SELECTION_PADDING_PX,
  STAGE_MAX_HEIGHT_RATIO,
  ZOOM_LIMITS,
  ZOOM_WHEEL_SPEED,
} from "../../constants/editor";
import useFontsLoaded from "../../hooks/useFontsLoaded";
import InlineTextEditor from "./InlineTextEditor";
import LayerToolbar, { LAYER_TOOLBAR_HEIGHT, LAYER_TOOLBAR_WIDTH } from "./LayerToolbar";
import { snapToGuides, toSnapBox, type SnapBox, type SnapGuide } from "./snapGuides";
import { resolveLayerFont, toCssFont, type TextLayer } from "./textLayer";
import TextLayerNode, {
  SELECTION_OUTLINE_NAME,
  TEXT_LAYER_NODE_NAME,
  type TextLayerSize,
} from "./TextLayerNode";
import styles from "./EditorCanvas.module.css";

// 글꼴을 미리 받을 때 쓰는 글자 크기 (크기와 상관없이 같은 파일을 받으므로 아무 값이나 됨)
const FONT_LOAD_SIZE_PX = 32;
// 모서리 핸들 크기 (화면 px)
const ANCHOR_SIZE_PX = 10;
// 회전 핸들이 선택 테두리에서 떨어진 거리 (화면 px)
const ROTATE_ANCHOR_OFFSET_PX = 24;
// 회전할 때 이 각도 가까이에서 살짝 붙는다
const ROTATION_SNAPS = [-180, -135, -90, -45, 0, 45, 90, 135, 180];
const ROTATION_SNAP_TOLERANCE = 4;
// 상자 위 도구줄과 선택 테두리 사이 간격. 회전 핸들을 가리지 않게 띄운다 (화면 px)
const TOOLBAR_GAP_PX = 44;
// 끌 때 상자의 모서리·가운데가 맞출 선(캔버스 가운데선, 다른 상자)에 이만큼 가까워지면 붙는다 (화면 px)
const SNAP_PX = 8;
// 맞춤 안내선의 두께와 점선 길이 (화면 px), 불투명도
const GUIDE_WIDTH_PX = 1;
const GUIDE_DASH_PX = 6;
const GUIDE_OPACITY = 0.75;
// 핸들을 끌어 상자를 이보다 작게 줄이지 못하게 한다 (화면 px)
const MIN_BOX_SIZE_PX = 16;
// 줄 단위로 알려주는 휠 입력(deltaMode 1)을 px로 바꿀 때 쓰는 한 줄 높이
const WHEEL_LINE_HEIGHT_PX = 16;
// 네 모서리 핸들만 쓴다
const CORNER_ANCHORS = ["top-left", "top-right", "bottom-left", "bottom-right"];

/**
 * 문구 상자가 캔버스에서 차지하는 테두리를 구한다. 배경 상자가 있으면 배경 상자 테두리 기준이다.
 *
 * @param layer - 문구 상자
 * @param size - 그려진 글자 크기 (원본 px, 배경 여백 제외)
 * @param x - 가운데 x (원본 px)
 * @param y - 가운데 y (원본 px)
 * @param imageHeight - 원본 이미지 높이 (배경 여백 비율을 px로 바꾸는 데 쓴다)
 * @returns 테두리 (회전한 상자는 회전한 모양을 감싸는 테두리)
 */
function layerSnapBox(
  layer: TextLayer,
  size: TextLayerSize,
  x: number,
  y: number,
  imageHeight: number,
): SnapBox {
  const padding = (layer.background?.padding ?? 0) * imageHeight;
  return toSnapBox(x, y, size.width + padding * 2, size.height + padding * 2, layer.rotation);
}

export interface EditorCanvasHandle {
  /**
   * 이미지와 문구를 합쳐 원본 해상도 PNG로 만든다. 선택 테두리는 넣지 않는다.
   *
   * @returns PNG 파일 데이터
   */
  toBlob: () => Promise<Blob>;
}

/**
 * 상자를 고르는 방식.
 * press: 상자를 누름 (이미 선택된 상자면 여러 개 선택을 그대로 두어 함께 끌 수 있게, 아니면 그 상자만),
 * toggle: Ctrl(⌘)을 누른 채 누름 (선택에 더하거나 뺌), only: 그 상자만 선택 (끌지 않고 클릭했을 때)
 */
export type SelectMode = "press" | "toggle" | "only";

type LayerChanges = Partial<Omit<TextLayer, "id">>;

export interface EditorCanvasProps {
  /** PNG 이미지의 base64 문자열 */
  imageBase64: string;
  /** 원본 이미지 크기(px) */
  imageWidth: number;
  imageHeight: number;
  /** 그릴 문구 상자 (뒤에 있을수록 위) */
  layers: TextLayer[];
  /** 선택한 문구 상자 id (선택한 순서) */
  selectedIds: string[];
  /** 직접 입력 중인 문구 상자 id */
  editingId: string | null;
  /** 문구 상자를 누르면 그 id와 고르는 방식, 빈 곳을 누르면 null */
  onSelect: (id: string | null, mode: SelectMode) => void;
  onStartEdit: (id: string) => void;
  /** 입력 칸 바깥을 누르거나 Esc를 누르면 호출 */
  onEndEdit: () => void;
  onChange: (id: string, changes: LayerChanges) => void;
  /** 여러 상자를 함께 끌었을 때 바뀐 위치를 한 번에 알린다 (되돌리기 한 단계) */
  onChangeMany: (changesById: Record<string, LayerChanges>) => void;
  onDuplicate: (id: string) => void;
  onDelete: (id: string) => void;
  /** 확대 배율 (원본 대비). null이면 편집 영역에 맞춘다 */
  zoom: number | null;
  /** 캔버스 위에서 휠을 굴려 배율을 바꿀 때 호출 */
  onZoomChange: (zoom: number) => void;
  /** 실제로 적용된 배율이 바뀔 때 호출 (도구줄의 % 표시용) */
  onScaleChange: (scale: number) => void;
}

/**
 * 값을 범위 안으로 맞춘다.
 *
 * @param value - 값
 * @param limit - 최솟값과 최댓값
 * @returns 범위 안의 값
 */
function clamp(value: number, { min, max }: { min: number; max: number }): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * 각도를 -180~180 범위로 맞추고 계산 오차를 없앤다.
 *
 * @param degrees - 각도
 * @returns 소수 첫째 자리까지의 각도
 */
function normalizeRotation(degrees: number): number {
  const positive = ((degrees % 360) + 360) % 360;
  return Math.round((positive > 180 ? positive - 360 : positive) * 10) / 10;
}

/**
 * base64 이미지를 캔버스에 그릴 수 있는 이미지 요소로 읽는다.
 *
 * @param base64 - PNG 이미지의 base64 문자열
 * @returns 다 읽었으면 이미지 요소, 읽는 중이면 null
 */
function useImageElement(base64: string): HTMLImageElement | null {
  const [image, setImage] = useState<HTMLImageElement | null>(null);

  useEffect(() => {
    let ignore = false;
    const element = new Image();
    element.onload = () => {
      if (!ignore) setImage(element);
    };
    element.src = `data:image/png;base64,${base64}`;
    return () => {
      ignore = true;
    };
  }, [base64]);

  return image;
}

/**
 * 화면에 들어오는 크기로 줄인 캔버스에 이미지와 문구 상자를 그린다.
 * 캔버스 안의 좌표는 원본 이미지 px 그대로이고, 화면 크기에 맞춰 배율만 바꾼다.
 * 그래서 저장할 때 배율을 되돌리면 원본 해상도 그대로 나온다.
 *
 * @param props - 이미지, 문구 상자, 선택·입력 상태와 처리 함수
 * @param ref - 편집본 이미지 만들기(toBlob)
 * @returns 편집 영역
 */
const EditorCanvas = forwardRef<EditorCanvasHandle, EditorCanvasProps>(function EditorCanvas(
  {
    imageBase64,
    imageWidth,
    imageHeight,
    layers,
    selectedIds,
    editingId,
    onSelect,
    onStartEdit,
    onEndEdit,
    onChange,
    onChangeMany,
    onDuplicate,
    onDelete,
    zoom,
    onZoomChange,
    onScaleChange,
  },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const transformerRef = useRef<Konva.Transformer>(null);
  // 문구 상자 id → 그려진 Konva 노드 (선택 테두리를 붙일 대상)
  const nodesRef = useRef(new Map<string, Konva.Group>());
  const [sizes, setSizes] = useState<Record<string, TextLayerSize>>({});
  const [available, setAvailable] = useState({ width: 0, height: 0 });
  // 끌거나 크기·각도를 바꾸는 동안은 상자 위 도구줄을 숨긴다
  const [interacting, setInteracting] = useState(false);
  // 상자를 끄는 동안 캔버스 가운데선이나 다른 상자에 맞춰져 있으면 그 안내선을 보여준다
  const [guides, setGuides] = useState<SnapGuide[]>([]);
  // 끄는 중인 상자와, 함께 움직이는 다른 선택 상자들의 끌기 시작 위치 (원본 px)
  const dragRef = useRef<{
    id: string;
    origin: { x: number; y: number };
    companions: Map<string, { x: number; y: number }>;
  } | null>(null);
  const multiSelected = selectedIds.length > 1;
  // 빈 곳을 끌어 캔버스를 옮기는 중이면 true
  const [panning, setPanning] = useState(false);
  // 휠 이벤트가 렌더보다 빠르게 와도 이어서 계산하도록 지금 배율을 따로 기억한다
  const scaleRef = useRef(0);
  // 휠로 확대할 때 마우스 아래에 붙잡아 둘 지점 (화면 위치, 원본 이미지 px)
  const wheelAnchorRef = useRef<{
    clientX: number;
    clientY: number;
    imageX: number;
    imageY: number;
  } | null>(null);
  const image = useImageElement(imageBase64);

  // 쓰는 글꼴을 미리 받고, 다 받으면 문구를 새로 그려 크기를 다시 잰다
  const fontsVersion = useFontsLoaded(
    layers.map((layer) => toCssFont(resolveLayerFont(layer), FONT_LOAD_SIZE_PX)),
  );

  // 편집 영역의 폭과 화면 높이에 맞춰 캔버스 크기를 정한다
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const measure = () =>
      setAvailable({
        width: container.clientWidth,
        height: window.innerHeight * STAGE_MAX_HEIGHT_RATIO,
      });
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    window.addEventListener("resize", measure);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  // 맞춤 배율은 원본보다 크게 늘리지 않는다. 내림해서 영역에 딱 맞을 때 스크롤이 생기지 않게 한다
  const fitScale = Math.min(1, available.width / imageWidth, available.height / imageHeight) || 0;
  const scale = fitScale > 0 ? (zoom ?? fitScale) : 0;
  const stageWidth = Math.floor(imageWidth * scale);
  const stageHeight = Math.floor(imageHeight * scale);
  // 편집 영역 높이는 맞춤 배율일 때의 이미지 높이로 고정한다.
  // 확대·축소해도 영역은 그대로이고, 그 안에서 이미지만 커지고 작아진다
  const areaHeight = Math.floor(imageHeight * fitScale);
  // 확대해서 편집 영역보다 커졌을 때만 끌어서 옮길 수 있다
  const pannable = stageWidth > available.width || stageHeight > areaHeight;

  useEffect(() => {
    if (scale > 0) onScaleChange(scale);
  }, [scale, onScaleChange]);

  // 배율이 바뀐 뒤, 마우스 아래 지점이 그대로 있도록 스크롤을 맞춘다
  useLayoutEffect(() => {
    scaleRef.current = scale;
    const anchor = wheelAnchorRef.current;
    const container = containerRef.current;
    const frame = frameRef.current;
    wheelAnchorRef.current = null;
    if (!anchor || !container || !frame) return;
    const rect = frame.getBoundingClientRect();
    container.scrollLeft += rect.left + anchor.imageX * scale - anchor.clientX;
    container.scrollTop += rect.top + anchor.imageY * scale - anchor.clientY;
  }, [scale]);

  // 캔버스 위 휠은 스크롤 대신 확대·축소로 쓴다. 페이지 스크롤을 막아야 해서 passive가 아닌
  // 리스너를 직접 단다 (React의 onWheel에서는 기본 동작을 막을 수 없다)
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    function handleWheel(e: WheelEvent) {
      const current = scaleRef.current;
      const frame = frameRef.current;
      if (current === 0 || !frame) return;
      e.preventDefault();

      const delta = e.deltaMode === 1 ? e.deltaY * WHEEL_LINE_HEIGHT_PX : e.deltaY;
      const next = Math.min(
        ZOOM_LIMITS.max,
        Math.max(ZOOM_LIMITS.min, current * Math.exp(-delta * ZOOM_WHEEL_SPEED)),
      );
      if (next === current) return;

      const rect = frame.getBoundingClientRect();
      wheelAnchorRef.current = {
        clientX: e.clientX,
        clientY: e.clientY,
        imageX: (e.clientX - rect.left) / current,
        imageY: (e.clientY - rect.top) / current,
      };
      scaleRef.current = next;
      onZoomChange(next);
    }
    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => container.removeEventListener("wheel", handleWheel);
  }, [onZoomChange]);

  // 하나만 선택하면 테두리와 크기·회전 핸들(Transformer)을 붙인다. 입력 중에는 입력 칸이 테두리를 대신한다.
  // 여러 개 선택이면 붙이지 않는다: Transformer는 붙은 노드들을 스스로 함께 끌어 상자마다 끌기 끝 이벤트가
  // 따로 나므로, 함께 끌기는 handleSnap이 맡고 테두리는 상자마다 TextLayerNode가 그린다
  useEffect(() => {
    const transformer = transformerRef.current;
    if (!transformer) return;
    const node =
      selectedIds.length === 1 && selectedIds[0] !== editingId
        ? nodesRef.current.get(selectedIds[0])
        : undefined;
    transformer.nodes(node ? [node] : []);
    // 묶음 안의 글자·배경 크기가 바뀐 것은 테두리가 스스로 알지 못해 직접 다시 맞춘다
    transformer.forceUpdate();
    transformer.getLayer()?.batchDraw();
  }, [selectedIds, editingId, layers, fontsVersion]);

  useImperativeHandle(
    ref,
    () => ({
      async toBlob() {
        const stage = stageRef.current;
        if (!stage || scale === 0) throw new Error("편집 영역이 아직 준비되지 않았어요");
        const transformer = transformerRef.current;

        // 잠깐 원본 크기로 되돌려 그린다. 배율로 늘려 저장하면 반올림으로 1px 어긋날 수 있다.
        // 화면을 다시 그리기 전에 끝나는 동기 작업이라 깜빡이지 않는다
        // 선택 테두리(하나: Transformer, 여러 개: 상자마다 그린 테두리)는 넣지 않는다
        const outlines = stage.find(`.${SELECTION_OUTLINE_NAME}`);
        transformer?.visible(false);
        outlines.forEach((outline) => outline.visible(false));
        stage.size({ width: imageWidth, height: imageHeight });
        stage.scale({ x: 1, y: 1 });
        let canvas: HTMLCanvasElement;
        try {
          canvas = stage.toCanvas({ pixelRatio: 1 });
        } finally {
          stage.size({ width: stageWidth, height: stageHeight });
          stage.scale({ x: scale, y: scale });
          transformer?.visible(true);
          outlines.forEach((outline) => outline.visible(true));
        }

        return new Promise<Blob>((resolve, reject) => {
          canvas.toBlob((blob) => {
            if (blob) resolve(blob);
            else reject(new Error("편집본 이미지를 만들지 못했어요"));
          }, "image/png");
        });
      },
    }),
    [imageWidth, imageHeight, scale, stageWidth, stageHeight],
  );

  /**
   * 빈 곳을 끄는 동안 마우스가 움직인 만큼 편집 영역 스크롤을 옮긴다.
   * 마우스가 캔버스 밖으로 나가도 이어지도록 window에서 듣는다.
   *
   * @param start - 끌기를 시작한 마우스 이벤트
   */
  function startPan(start: MouseEvent) {
    const container = containerRef.current;
    if (!container) return;
    const { scrollLeft, scrollTop } = container;

    function handleMove(e: MouseEvent) {
      if (!container) return;
      container.scrollLeft = scrollLeft - (e.clientX - start.clientX);
      container.scrollTop = scrollTop - (e.clientY - start.clientY);
    }
    function handleUp() {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
      setPanning(false);
    }
    setPanning(true);
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
  }

  const handleRegister = useCallback((id: string, node: Konva.Group | null) => {
    if (node) nodesRef.current.set(id, node);
    else nodesRef.current.delete(id);
  }, []);

  // 크기가 그대로면 상태를 바꾸지 않아, 매 렌더마다 재는 TextLayerNode와 서로 다시 그리기를 반복하지 않는다
  const handleMeasure = useCallback((id: string, size: TextLayerSize) => {
    setSizes((prev) => {
      const old = prev[id];
      if (old && old.width === size.width && old.height === size.height) return prev;
      return { ...prev, [id]: size };
    });
  }, []);

  /**
   * 끄는 상자를 캔버스 가운데선과 다른 상자의 모서리·가운데에 맞춘 위치를 구하고 안내선을 보여준다.
   * 끄는 상자가 여러 개 선택 중 하나면, 다른 선택 상자도 같은 거리만큼 함께 옮긴다
   * (함께 움직이는 상자는 맞출 대상에서 뺀다). 상자 가운데는 이미지 밖으로 나가지 않는다.
   */
  const handleSnap = useCallback(
    (id: string, x: number, y: number) => {
      const clampTo = (value: number, max: number) => Math.min(max, Math.max(0, value));
      const dragging = layers.find((layer) => layer.id === id);
      const size = sizes[id];
      if (!dragging || !size) {
        setGuides((prev) => (prev.length === 0 ? prev : []));
        return { x: clampTo(x, imageWidth), y: clampTo(y, imageHeight) };
      }
      // 끌기를 시작할 때 함께 움직일 상자와 시작 위치를 기억한다
      if (dragRef.current?.id !== id) {
        const companions = new Map<string, { x: number; y: number }>();
        if (selectedIds.includes(id)) {
          for (const layer of layers) {
            if (layer.id !== id && selectedIds.includes(layer.id)) {
              companions.set(layer.id, { x: layer.x * imageWidth, y: layer.y * imageHeight });
            }
          }
        }
        dragRef.current = {
          id,
          origin: { x: dragging.x * imageWidth, y: dragging.y * imageHeight },
          companions,
        };
      }
      const { origin, companions } = dragRef.current;
      const others = layers
        .filter((layer) => layer.id !== id && !companions.has(layer.id) && sizes[layer.id])
        .map((layer) =>
          layerSnapBox(
            layer,
            sizes[layer.id],
            layer.x * imageWidth,
            layer.y * imageHeight,
            imageHeight,
          ),
        );
      const moving = layerSnapBox(dragging, size, x, y, imageHeight);
      // 배율이 달라도 화면에서 같은 거리로 붙도록 화면 px를 원본 px로 바꾼다
      const threshold = SNAP_PX / (scaleRef.current || 1);
      const {
        dx,
        dy,
        guides: next,
      } = snapToGuides(moving, others, imageWidth, imageHeight, threshold);
      // 안내선이 그대로면 상태를 바꾸지 않아, 끄는 동안 캔버스를 불필요하게 다시 그리지 않는다
      setGuides((prev) => (JSON.stringify(prev) === JSON.stringify(next) ? prev : next));
      const snapped = { x: clampTo(x + dx, imageWidth), y: clampTo(y + dy, imageHeight) };
      for (const [companionId, start] of companions) {
        nodesRef.current.get(companionId)?.position({
          x: clampTo(start.x + snapped.x - origin.x, imageWidth),
          y: clampTo(start.y + snapped.y - origin.y, imageHeight),
        });
      }
      return snapped;
    },
    [layers, sizes, selectedIds, imageWidth, imageHeight],
  );

  const handleSnapEnd = useCallback(() => setGuides([]), []);

  // 끌기가 끝나면 새 위치를 저장한다. 함께 움직인 상자가 있으면 한 번에 저장해 되돌리기 한 단계로 만든다
  const handleMove = useCallback(
    (id: string, x: number, y: number) => {
      const companions = dragRef.current?.id === id ? dragRef.current.companions : null;
      dragRef.current = null;
      if (!companions || companions.size === 0) {
        onChange(id, { x, y });
        return;
      }
      const changes: Record<string, LayerChanges> = { [id]: { x, y } };
      for (const companionId of companions.keys()) {
        const node = nodesRef.current.get(companionId);
        if (node) changes[companionId] = { x: node.x() / imageWidth, y: node.y() / imageHeight };
      }
      onChangeMany(changes);
    },
    [onChange, onChangeMany, imageWidth, imageHeight],
  );

  // 크기를 바꾸면 외곽선·그림자·배경 여백도 같은 배율로 맞춰 모양을 유지한다
  const handleTransform = useCallback(
    (id: string, ratio: number, x: number, y: number, rotation: number) => {
      const layer = layers.find((item) => item.id === id);
      if (!layer) return;
      const limits = LAYER_LIMITS;
      const { stroke, shadow, background } = layer;
      onChange(id, {
        x: Math.min(1, Math.max(0, x)),
        y: Math.min(1, Math.max(0, y)),
        rotation: normalizeRotation(rotation),
        fontSize: clamp(layer.fontSize * ratio, limits.fontSize),
        width: layer.width === null ? null : clamp(layer.width * ratio, limits.width),
        stroke: stroke && { ...stroke, width: clamp(stroke.width * ratio, limits.strokeWidth) },
        shadow: shadow && {
          ...shadow,
          blur: clamp(shadow.blur * ratio, limits.shadowBlur),
          offsetX: clamp(shadow.offsetX * ratio, limits.shadowOffset),
          offsetY: clamp(shadow.offsetY * ratio, limits.shadowOffset),
        },
        background: background && {
          ...background,
          padding: clamp(background.padding * ratio, limits.backgroundPadding),
          radius: clamp(background.radius * ratio, limits.backgroundRadius),
        },
      });
    },
    [layers, onChange],
  );

  const editingLayer = layers.find((layer) => layer.id === editingId);
  // 캔버스는 CSS 변수를 직접 못 쓰므로 디자인 토큰 값을 읽어 선택 테두리 색으로 쓴다
  const selectionColor =
    getComputedStyle(document.documentElement).getPropertyValue("--color-primary").trim() ||
    "#4f4be8";

  // 캔버스 좌표는 원본 px이므로, 배율로 나눠 화면에서 항상 같은 두께·길이로 보이게 한다
  const guideStyle = {
    stroke: selectionColor,
    strokeWidth: GUIDE_WIDTH_PX / scale,
    dash: [GUIDE_DASH_PX / scale, GUIDE_DASH_PX / scale],
    opacity: GUIDE_OPACITY,
    listening: false,
  };

  // 선택한 상자 위 도구줄 위치. 여러 개 선택·입력·끌기 중에는 숨기고, 위에 자리가 없으면 상자 아래에 둔다
  const selectedId = selectedIds.length === 1 ? selectedIds[0] : null;
  const selectedLayer = layers.find((layer) => layer.id === selectedId);
  const selectedSize = selectedId ? sizes[selectedId] : undefined;
  let toolbarPosition: { left: number; top: number } | null = null;
  if (selectedLayer && selectedSize && !editingId && !interacting) {
    const centerX = selectedLayer.x * imageWidth * scale;
    const centerY = selectedLayer.y * imageHeight * scale;
    // 회전한 상자가 위아래로 차지하는 높이의 절반 (배경 상자 여백 포함)
    const padding = (selectedLayer.background?.padding ?? 0) * imageHeight;
    const radians = (selectedLayer.rotation * Math.PI) / 180;
    const boxWidth = (selectedSize.width + padding * 2) * scale;
    const boxHeight = (selectedSize.height + padding * 2) * scale;
    const halfHeight =
      (Math.abs(boxWidth * Math.sin(radians)) + Math.abs(boxHeight * Math.cos(radians))) / 2 +
      SELECTION_PADDING_PX +
      TOOLBAR_GAP_PX;
    const above = centerY - halfHeight - LAYER_TOOLBAR_HEIGHT;
    toolbarPosition = {
      left: Math.max(
        0,
        Math.min(stageWidth - LAYER_TOOLBAR_WIDTH, centerX - LAYER_TOOLBAR_WIDTH / 2),
      ),
      top: above >= 0 ? above : Math.min(stageHeight - LAYER_TOOLBAR_HEIGHT, centerY + halfHeight),
    };
  }

  return (
    <div
      ref={containerRef}
      className={styles.container}
      style={areaHeight > 0 ? { height: areaHeight } : undefined}
      // 이미지 바깥 회색 바탕을 눌러도 선택을 푼다 (스크롤 막대를 누를 때는 제외). 끌어 옮기지는 않는다
      onMouseDown={(e) => {
        const area = e.currentTarget;
        const onScrollbar =
          e.nativeEvent.offsetX >= area.clientWidth || e.nativeEvent.offsetY >= area.clientHeight;
        if (e.target === area && !onScrollbar) onSelect(null, "only");
      }}
    >
      {scale > 0 && (
        <div
          ref={frameRef}
          className={`${styles.frame} ${pannable ? styles.pannable : ""} ${panning ? styles.panning : ""}`}
          style={{ width: stageWidth, height: stageHeight }}
        >
          <Stage
            ref={stageRef}
            width={stageWidth}
            height={stageHeight}
            scaleX={scale}
            scaleY={scale}
            // 이미지(빈 곳)를 누르면 선택을 풀고, 확대 중이면 끌어서 옮기기를 시작한다
            onMouseDown={(e) => {
              if (e.target === e.target.getStage() || e.target.name() === "background") {
                onSelect(null, "only");
                if (pannable) startPan(e.evt);
              }
            }}
            // 문구 위에서는 옮길 수 있다는 커서를 보여주고, 그 밖에는 바깥 칸의 커서를 따른다
            onMouseMove={(e) => {
              const container = e.target.getStage()?.container();
              if (container) {
                const onLayer = e.target.findAncestor(`.${TEXT_LAYER_NODE_NAME}`);
                container.style.cursor = onLayer ? "move" : "";
              }
            }}
            onTouchStart={(e) => {
              if (e.target === e.target.getStage() || e.target.name() === "background") {
                onSelect(null, "only");
              }
            }}
          >
            <Layer>
              {image && (
                <KonvaImage
                  name="background"
                  image={image}
                  width={imageWidth}
                  height={imageHeight}
                />
              )}
              {layers.map((layer) => (
                <TextLayerNode
                  // 글꼴을 다 받으면 노드를 새로 만들어 바뀐 글꼴로 크기를 다시 잰다
                  key={`${layer.id}-${fontsVersion}`}
                  layer={layer}
                  imageWidth={imageWidth}
                  imageHeight={imageHeight}
                  editing={layer.id === editingId}
                  outlineColor={
                    multiSelected && selectedIds.includes(layer.id) ? selectionColor : null
                  }
                  onRegister={handleRegister}
                  onMeasure={handleMeasure}
                  onPress={(id, additive) => onSelect(id, additive ? "toggle" : "press")}
                  onClick={(id, additive) => {
                    if (!additive) onSelect(id, "only");
                  }}
                  onStartEdit={onStartEdit}
                  onMove={handleMove}
                  onTransform={handleTransform}
                  onSnap={handleSnap}
                  onSnapEnd={handleSnapEnd}
                  onInteract={setInteracting}
                />
              ))}
              {guides.map((points) => (
                <Line key={points.join(",")} points={points} {...guideStyle} />
              ))}
              <Transformer
                ref={transformerRef}
                rotateAnchorOffset={ROTATE_ANCHOR_OFFSET_PX}
                rotationSnaps={ROTATION_SNAPS}
                rotationSnapTolerance={ROTATION_SNAP_TOLERANCE}
                flipEnabled={false}
                keepRatio
                enabledAnchors={CORNER_ANCHORS}
                anchorSize={ANCHOR_SIZE_PX}
                anchorStroke={selectionColor}
                borderStroke={selectionColor}
                borderStrokeWidth={1.5}
                padding={SELECTION_PADDING_PX}
                boundBoxFunc={(oldBox, newBox) =>
                  Math.abs(newBox.width) < MIN_BOX_SIZE_PX ||
                  Math.abs(newBox.height) < MIN_BOX_SIZE_PX
                    ? oldBox
                    : newBox
                }
              />
            </Layer>
          </Stage>

          {toolbarPosition && selectedLayer && (
            <LayerToolbar
              left={toolbarPosition.left}
              top={toolbarPosition.top}
              onEdit={() => onStartEdit(selectedLayer.id)}
              onDuplicate={() => onDuplicate(selectedLayer.id)}
              onDelete={() => onDelete(selectedLayer.id)}
            />
          )}

          {editingLayer && (
            <InlineTextEditor
              layer={editingLayer}
              size={sizes[editingLayer.id]}
              imageWidth={imageWidth}
              imageHeight={imageHeight}
              scale={scale}
              onChange={(text) => onChange(editingLayer.id, { text })}
              onDone={onEndEdit}
            />
          )}
        </div>
      )}
    </div>
  );
});

export default EditorCanvas;
