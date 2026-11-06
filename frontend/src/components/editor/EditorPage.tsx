/**
 * 텍스트 에디터 화면 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-06
 * 수정자: bioyejin
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, Download, Eye, Minus, Plus, Redo2, RotateCcw, Save, Undo2 } from "lucide-react";
import type { GenerateResponse } from "../../api/client";
import { DUPLICATE_OFFSET, LAYER_LIMITS, ZOOM_LIMITS } from "../../constants/editor";
import type { TextLayers } from "../../hooks/useTextLayers";
import Button from "../common/Button";
import Modal from "../common/Modal";
import { pickTextColor } from "./autoColor";
import { base64ToBlob, downloadBlob, toImageFileName } from "./download";
import EditorCanvas, { type EditorCanvasHandle } from "./EditorCanvas";
import EditorOverlay from "./EditorOverlay";
import EditorSidePanel from "./EditorSidePanel";
import { createTextLayer } from "./textLayer";
import TextLayerPanel from "./TextLayerPanel";
import ThumbnailStrip from "./ThumbnailStrip";
import styles from "./EditorPage.module.css";

// 글자를 입력받지 않는 input 종류
const NON_TEXT_INPUT_TYPES = ["range", "color", "checkbox", "radio", "button"];

export interface EditorPageProps {
  result: GenerateResponse;
  /** 편집 중인 이미지 순서(0부터) */
  index: number;
  /** 썸네일을 눌러 다른 이미지를 고를 때 호출 */
  onIndexChange: (index: number) => void;
  /** [← 이전 화면으로]를 누를 때 호출 */
  onBack: () => void;
  /** 이미지별 문구 상자 (에디터를 나갔다 와도 유지되도록 바깥에서 관리) */
  textLayers: TextLayers;
}

/**
 * 키 입력이 글자 입력 칸에서 일어났는지 확인한다 (그때는 Delete로 상자를 지우지 않는다).
 *
 * @param target - 키 이벤트가 일어난 요소
 * @returns 입력 칸이면 true
 */
function isTypingTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

/**
 * Ctrl+Z를 브라우저의 글자 되돌리기에 맡길 곳인지 확인한다.
 * 슬라이더나 색 선택 칸은 글자를 받지 않으므로 문구 상자 되돌리기를 쓴다.
 *
 * @param target - 키 이벤트가 일어난 요소
 * @returns 글자를 입력하는 칸이면 true
 */
function usesNativeUndo(target: EventTarget | null): boolean {
  if (target instanceof HTMLInputElement && NON_TEXT_INPUT_TYPES.includes(target.type)) {
    return false;
  }
  return isTypingTarget(target);
}

/**
 * 지금 배율에서 확대·축소 단계로 한 칸 옮긴 배율을 구한다. 맞춤 배율(예: 66%)에서는 가까운 단계로 맞춘다.
 *
 * @param scale - 지금 배율
 * @param direction - 확대면 1, 축소면 -1
 * @returns 범위 안의 새 배율
 */
function stepZoom(scale: number, direction: 1 | -1): number {
  const { min, max, step } = ZOOM_LIMITS;
  const position = scale / step;
  // 소수 오차로 지금 단계에 머무르지 않도록 아주 작은 값을 더하고 뺀다
  const next = direction > 0 ? Math.floor(position + 1e-6) + 1 : Math.ceil(position - 1e-6) - 1;
  return Math.min(max, Math.max(min, next * step));
}

/**
 * 위에 돌아가기·리셋·미리보기·저장 버튼, 왼쪽에 캔버스 카드(확대·축소, 캔버스, 썸네일),
 * 오른쪽에 탭 패널이 있는 편집 화면. 문구 상자를 추가해 이미지 위에서 바로 입력하고 옮길 수 있으며,
 * 원본이나 문구를 합친 편집본을 원본 해상도 PNG로 저장한다.
 *
 * @param props - 생성 결과, 편집 중인 이미지 순서, 문구 상자, 이미지 고르기·돌아가기 처리 함수
 * @returns 에디터 화면
 */
export default function EditorPage({
  result,
  index,
  onIndexChange,
  onBack,
  textLayers,
}: EditorPageProps) {
  const canvasRef = useRef<EditorCanvasHandle>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  // 글꼴 메뉴에서 항목을 옮겨 다닐 때 캔버스에만 임시로 입히는 글꼴 (저장값은 그대로)
  const [previewFontId, setPreviewFontId] = useState<string | null>(null);
  // 확대 배율. null이면 편집 영역에 맞춘다
  const [zoom, setZoom] = useState<number | null>(null);
  const [scale, setScale] = useState(0);
  const [saveOpen, setSaveOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  // 미리보기로 띄운 합성 이미지의 임시 주소
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const image = result.images[index];
  const layers = textLayers.layersOf(index);
  const selectedLayer = layers.find((layer) => layer.id === selectedId) ?? null;
  const shownLayers = previewFontId
    ? layers.map((layer) => (layer.id === selectedId ? { ...layer, fontId: previewFontId } : layer))
    : layers;
  const overlayOpen = saveOpen || resetOpen || previewUrl !== null;

  // 다른 이미지로 바꾸면 선택과 입력을 풀고 확대도 기본(화면 맞춤)으로 되돌린다
  useEffect(() => {
    setSelectedId(null);
    setEditingId(null);
    setNotice(null);
    setZoom(null);
  }, [index]);

  // 선택이 바뀌면 임시 글꼴을 지운다
  useEffect(() => {
    setPreviewFontId(null);
  }, [selectedId]);

  // 되돌리기로 선택한 상자가 없어지면 선택을 푼다
  useEffect(() => {
    if (selectedId && !selectedLayer) setSelectedId(null);
  }, [selectedId, selectedLayer]);

  // 미리보기를 닫거나 화면을 나가면 임시 주소를 정리한다
  useEffect(() => {
    if (!previewUrl) return;
    return () => URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  // 상자를 선택한 채 Delete(맥은 Backspace)를 누르면 지운다. 글자 입력 중이나 팝업이 열려 있으면 지우지 않는다
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (!selectedId || editingId || overlayOpen || isTypingTarget(e.target)) return;
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        textLayers.remove(index, selectedId);
        setSelectedId(null);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedId, editingId, overlayOpen, index, textLayers]);

  // Ctrl+Z로 되돌리고 Ctrl+Y나 Ctrl+Shift+Z로 다시 실행한다 (맥은 Cmd). 글자 입력 중이나 팝업이 열려 있으면 쓰지 않는다
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
      if (editingId || overlayOpen || usesNativeUndo(e.target)) return;
      const key = e.key.toLowerCase();
      if (key !== "z" && key !== "y") return;
      e.preventDefault();
      if (key === "y" || e.shiftKey) textLayers.redo(index);
      else textLayers.undo(index);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [editingId, overlayOpen, index, textLayers]);

  const closeSave = useCallback(() => {
    setSaveOpen(false);
    setSaveError(null);
  }, []);
  const closePreview = useCallback(() => setPreviewUrl(null), []);

  if (!image) return null;

  /** 이미지 가운데에 새 문구 상자를 넣고 바로 입력 상태로 만든다. 글자색은 그 자리 밝기에 맞춘다. */
  async function handleAdd() {
    const color = await pickTextColor(image.image_base64, 0.5, 0.5);
    const layer = createTextLayer({ color });
    if (!textLayers.add(index, layer)) {
      setNotice(`문구 상자는 이미지 한 장에 ${LAYER_LIMITS.layerCount.max}개까지 넣을 수 있어요`);
      return;
    }
    setNotice(null);
    setSelectedId(layer.id);
    setEditingId(layer.id);
  }

  /** 입력을 끝낸다. 문구를 다 지웠으면 그 상자도 지운다. */
  function handleEndEdit() {
    const layer = layers.find((item) => item.id === editingId);
    if (layer && layer.text.trim() === "") {
      textLayers.removeEmpty(index, layer.id);
      setSelectedId(null);
    }
    textLayers.endChangeGroup(index);
    setEditingId(null);
  }

  /** 문구 상자를 지운다. */
  function handleDelete(id: string) {
    textLayers.remove(index, id);
    setSelectedId(null);
    setEditingId(null);
  }

  /** 문구 상자를 살짝 비켜 복제하고, 복제한 상자를 선택한다. */
  function handleDuplicate(id: string) {
    const source = layers.find((layer) => layer.id === id);
    if (!source) return;
    const copy = createTextLayer({
      ...source,
      x: Math.min(1, source.x + DUPLICATE_OFFSET),
      y: Math.min(1, source.y + DUPLICATE_OFFSET),
    });
    if (!textLayers.add(index, copy)) {
      setNotice(`문구 상자는 이미지 한 장에 ${LAYER_LIMITS.layerCount.max}개까지 넣을 수 있어요`);
      return;
    }
    setNotice(null);
    setSelectedId(copy.id);
  }

  /** 지금 이미지의 문구를 모두 지운다. */
  function handleReset() {
    textLayers.replace(index, []);
    setSelectedId(null);
    setEditingId(null);
    setNotice(null);
    setResetOpen(false);
  }

  /** 저장될 모습 그대로 합성한 이미지를 어두운 레이어 위에 띄운다. */
  async function handlePreview() {
    setNotice(null);
    try {
      const canvas = canvasRef.current;
      if (!canvas) throw new Error("편집 영역이 아직 준비되지 않았어요");
      setPreviewUrl(URL.createObjectURL(await canvas.toBlob()));
    } catch (error) {
      console.error("미리보기 실패", error);
      setNotice("미리보기를 만들지 못했어요. 잠시 후 다시 시도해 주세요");
    }
  }

  /** 지금 보고 있는 이미지를 서버가 보낸 원본 그대로 PNG로 내려받는다. */
  function handleSaveOriginal() {
    downloadBlob(base64ToBlob(image.image_base64), toImageFileName(image.seed));
    closeSave();
  }

  /** 지금 보고 있는 이미지에 문구를 합쳐 원본 해상도 PNG로 내려받는다. */
  async function handleSaveEdited() {
    setSaveError(null);
    try {
      const canvas = canvasRef.current;
      if (!canvas) throw new Error("편집 영역이 아직 준비되지 않았어요");
      downloadBlob(await canvas.toBlob(), toImageFileName(image.seed, true));
      closeSave();
    } catch (error) {
      console.error("편집본 저장 실패", error);
      setSaveError("편집본을 저장하지 못했어요. 잠시 후 다시 시도해 주세요");
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.toolbar}>
        <Button
          variant="ghost"
          className={styles.backButton}
          icon={<ArrowLeft size={18} />}
          onClick={onBack}
        >
          이전 화면으로
        </Button>
        <div className={styles.toolbarActions}>
          <Button
            variant="ghost"
            size="sm"
            icon={<Undo2 size={16} />}
            aria-label="되돌리기"
            title="되돌리기 (Ctrl+Z)"
            disabled={!textLayers.canUndo(index)}
            onClick={() => textLayers.undo(index)}
          />
          <Button
            variant="ghost"
            size="sm"
            icon={<Redo2 size={16} />}
            aria-label="다시 실행"
            title="다시 실행 (Ctrl+Y)"
            disabled={!textLayers.canRedo(index)}
            onClick={() => textLayers.redo(index)}
          />
          <Button
            icon={<RotateCcw size={14} />}
            disabled={layers.length === 0}
            onClick={() => setResetOpen(true)}
          >
            리셋
          </Button>
          <Button icon={<Eye size={14} />} onClick={handlePreview}>
            미리보기
          </Button>
          <Button variant="primary" icon={<Save size={14} />} onClick={() => setSaveOpen(true)}>
            저장하기
          </Button>
        </div>
      </div>

      <div className={styles.workspace}>
        <section className={styles.card} aria-label="편집 영역">
          <div className={styles.canvasTools}>
            <div className={styles.zoom}>
              <Button
                variant="ghost"
                size="sm"
                icon={<Minus size={16} />}
                aria-label="축소"
                disabled={scale <= ZOOM_LIMITS.min}
                onClick={() => setZoom(stepZoom(scale, -1))}
              />
              <button
                type="button"
                className={styles.zoomValue}
                title="화면에 맞추기"
                onClick={() => setZoom(null)}
              >
                {Math.round(scale * 100)}%
              </button>
              <Button
                variant="ghost"
                size="sm"
                icon={<Plus size={16} />}
                aria-label="확대"
                disabled={scale >= ZOOM_LIMITS.max}
                onClick={() => setZoom(stepZoom(scale, 1))}
              />
            </div>
            <span className={styles.resolution}>
              {result.width} × {result.height}
            </span>
          </div>

          <div className={styles.stage}>
            <EditorCanvas
              ref={canvasRef}
              imageBase64={image.image_base64}
              imageWidth={result.width}
              imageHeight={result.height}
              layers={shownLayers}
              selectedId={selectedId}
              editingId={editingId}
              onSelect={(id) => {
                setSelectedId(id);
                if (id !== editingId) setEditingId(null);
              }}
              onStartEdit={(id) => {
                setSelectedId(id);
                setEditingId(id);
              }}
              onEndEdit={handleEndEdit}
              onChange={(id, changes) => textLayers.update(index, id, changes)}
              onDuplicate={handleDuplicate}
              onDelete={handleDelete}
              zoom={zoom}
              onZoomChange={setZoom}
              onScaleChange={setScale}
            />
          </div>

          <ThumbnailStrip
            images={result.images}
            selectedIndex={index}
            width={result.width}
            height={result.height}
            onSelect={onIndexChange}
          />
        </section>

        <EditorSidePanel>
          <TextLayerPanel
            selectedLayer={selectedLayer}
            imageWidth={result.width}
            imageHeight={result.height}
            notice={notice}
            onAdd={handleAdd}
            onDelete={handleDelete}
            onChange={(id, changes) => textLayers.update(index, id, changes)}
            onTextEnd={() => textLayers.endChangeGroup(index)}
            onFontPreview={setPreviewFontId}
          />
        </EditorSidePanel>
      </div>

      <Modal
        open={resetOpen}
        title="이 이미지의 문구를 모두 지울까요?"
        confirmLabel="지우기"
        onConfirm={handleReset}
        onCancel={() => setResetOpen(false)}
      />

      {previewUrl && (
        <EditorOverlay label="편집본 미리보기" onClose={closePreview}>
          <img
            className={styles.previewImage}
            src={previewUrl}
            alt={`${result.original_prompt} 편집본 미리보기`}
          />
        </EditorOverlay>
      )}

      {saveOpen && (
        <EditorOverlay label="이미지 저장" onClose={closeSave}>
          <div className={styles.saveMenu}>
            <Button icon={<Download size={14} />} size="lg" onClick={handleSaveOriginal}>
              원본 저장
            </Button>
            <Button
              variant="primary"
              size="lg"
              icon={<Download size={14} />}
              onClick={handleSaveEdited}
            >
              편집본 저장
            </Button>
            <p className={styles.saveHint}>PNG 형식으로 한 장씩 저장돼요</p>
            {saveError && <p className={styles.saveError}>{saveError}</p>}
          </div>
        </EditorOverlay>
      )}
    </div>
  );
}
