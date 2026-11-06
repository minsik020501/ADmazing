/**
 * 이미지와 문구 상자를 그리는 편집 영역(캔버스) 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-06
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
import { resolveLayerFont, toCssFont, type TextLayer } from "./textLayer";
import TextLayerNode, { TEXT_LAYER_NODE_NAME, type TextLayerSize } from "./TextLayerNode";
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
// 가운데 안내선의 두께와 점선 길이 (화면 px), 불투명도
const GUIDE_WIDTH_PX = 1;
const GUIDE_DASH_PX = 6;
const GUIDE_OPACITY = 0.75;
// 핸들을 끌어 상자를 이보다 작게 줄이지 못하게 한다 (화면 px)
const MIN_BOX_SIZE_PX = 16;
// 줄 단위로 알려주는 휠 입력(deltaMode 1)을 px로 바꿀 때 쓰는 한 줄 높이
const WHEEL_LINE_HEIGHT_PX = 16;
// 네 모서리 핸들만 쓴다
const CORNER_ANCHORS = ["top-left", "top-right", "bottom-left", "bottom-right"];

export interface EditorCanvasHandle {
  /**
   * 이미지와 문구를 합쳐 원본 해상도 PNG로 만든다. 선택 테두리는 넣지 않는다.
   *
   * @returns PNG 파일 데이터
   */
  toBlob: () => Promise<Blob>;
}

export interface EditorCanvasProps {
  /** PNG 이미지의 base64 문자열 */
  imageBase64: string;
  /** 원본 이미지 크기(px) */
  imageWidth: number;
  imageHeight: number;
  /** 그릴 문구 상자 (뒤에 있을수록 위) */
  layers: TextLayer[];
  selectedId: string | null;
  /** 직접 입력 중인 문구 상자 id */
  editingId: string | null;
  /** 문구 상자를 누르면 그 id, 빈 곳을 누르면 null */
  onSelect: (id: string | null) => void;
  onStartEdit: (id: string) => void;
  /** 입력 칸 바깥을 누르거나 Esc를 누르면 호출 */
  onEndEdit: () => void;
  onChange: (id: string, changes: Partial<Omit<TextLayer, "id">>) => void;
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
    selectedId,
    editingId,
    onSelect,
    onStartEdit,
    onEndEdit,
    onChange,
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
  // 상자를 끄는 동안 이미지 가운데선에 붙어 있으면 그 선을 보여준다
  const [centerGuides, setCenterGuides] = useState({ vertical: false, horizontal: false });
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
  // 확대해서 편집 영역보다 커졌을 때만 끌어서 옮길 수 있다
  const pannable = stageWidth > available.width || stageHeight > available.height;

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

  // 선택한 상자에 테두리를 붙인다. 입력 중에는 입력 칸이 테두리를 대신한다
  useEffect(() => {
    const transformer = transformerRef.current;
    if (!transformer) return;
    const node = selectedId && selectedId !== editingId ? nodesRef.current.get(selectedId) : null;
    transformer.nodes(node ? [node] : []);
    // 묶음 안의 글자·배경 크기가 바뀐 것은 테두리가 스스로 알지 못해 직접 다시 맞춘다
    transformer.forceUpdate();
    transformer.getLayer()?.batchDraw();
  }, [selectedId, editingId, layers, fontsVersion]);

  useImperativeHandle(
    ref,
    () => ({
      async toBlob() {
        const stage = stageRef.current;
        if (!stage || scale === 0) throw new Error("편집 영역이 아직 준비되지 않았어요");
        const transformer = transformerRef.current;

        // 잠깐 원본 크기로 되돌려 그린다. 배율로 늘려 저장하면 반올림으로 1px 어긋날 수 있다.
        // 화면을 다시 그리기 전에 끝나는 동기 작업이라 깜빡이지 않는다
        transformer?.visible(false);
        stage.size({ width: imageWidth, height: imageHeight });
        stage.scale({ x: 1, y: 1 });
        let canvas: HTMLCanvasElement;
        try {
          canvas = stage.toCanvas({ pixelRatio: 1 });
        } finally {
          stage.size({ width: stageWidth, height: stageHeight });
          stage.scale({ x: scale, y: scale });
          transformer?.visible(true);
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

  // 붙은 상태가 그대로면 상태를 바꾸지 않아, 끄는 동안 캔버스를 불필요하게 다시 그리지 않는다
  const handleCenterSnap = useCallback((vertical: boolean, horizontal: boolean) => {
    setCenterGuides((prev) =>
      prev.vertical === vertical && prev.horizontal === horizontal
        ? prev
        : { vertical, horizontal },
    );
  }, []);

  const handleMove = useCallback(
    (id: string, x: number, y: number) => onChange(id, { x, y }),
    [onChange],
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

  // 선택한 상자 위 도구줄 위치. 입력·끌기 중에는 숨기고, 위에 자리가 없으면 상자 아래에 둔다
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
    <div ref={containerRef} className={styles.container}>
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
                onSelect(null);
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
                onSelect(null);
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
                  onRegister={handleRegister}
                  onMeasure={handleMeasure}
                  onSelect={onSelect}
                  onStartEdit={onStartEdit}
                  onMove={handleMove}
                  onTransform={handleTransform}
                  onCenterSnap={handleCenterSnap}
                  onInteract={setInteracting}
                />
              ))}
              {centerGuides.vertical && (
                <Line points={[imageWidth / 2, 0, imageWidth / 2, imageHeight]} {...guideStyle} />
              )}
              {centerGuides.horizontal && (
                <Line points={[0, imageHeight / 2, imageWidth, imageHeight / 2]} {...guideStyle} />
              )}
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
