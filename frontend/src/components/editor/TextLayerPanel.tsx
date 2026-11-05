/**
 * 에디터 오른쪽의 문구 패널 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
 * 수정자: bioyejin
 */

import { useEffect, useState, type ReactNode } from "react";
import {
  AlignCenter,
  AlignLeft,
  AlignRight,
  Bold,
  Italic,
  Plus,
  Strikethrough,
  Trash2,
} from "lucide-react";
import {
  FONT_SIZE_BUTTON_STEP_PX,
  LAYER_LIMITS,
  LINE_HEIGHT_BUTTON_STEP,
} from "../../constants/editor";
import Button from "../common/Button";
import ColorField from "./ColorField";
import FontPicker from "./FontPicker";
import NumberField from "./NumberField";
import SliderField from "./SliderField";
import TextEffectFields from "./TextEffectFields";
import type { TextAlign, TextLayer } from "./textLayer";
import styles from "./TextLayerPanel.module.css";

const ALIGN_OPTIONS: { value: TextAlign; label: string; icon: ReactNode }[] = [
  { value: "left", label: "왼쪽 정렬", icon: <AlignLeft size={16} /> },
  { value: "center", label: "가운데 정렬", icon: <AlignCenter size={16} /> },
  { value: "right", label: "오른쪽 정렬", icon: <AlignRight size={16} /> },
];

export interface TextLayerPanelProps {
  /** 선택한 문구 상자. 없으면 null */
  selectedLayer: TextLayer | null;
  /** 원본 이미지 크기(px). 글자 크기와 위치를 px로 보여주는 데 쓴다 */
  imageWidth: number;
  imageHeight: number;
  /** 상자를 더 넣을 수 없는 이유 등 패널 아래에 보여줄 안내. 없으면 null */
  notice: string | null;
  onAdd: () => void;
  onDelete: (id: string) => void;
  /** 선택한 문구 상자의 값을 바꾼다 */
  onChange: (id: string, changes: Partial<Omit<TextLayer, "id">>) => void;
  /** 글꼴 메뉴에서 항목으로 이동할 때 캔버스에 임시로 보여줄 글꼴 id. 끝나면 null */
  onFontPreview: (fontId: string | null) => void;
}

interface TextInputProps {
  /** 지금 문구 */
  value: string;
  onChange: (text: string) => void;
}

/**
 * 문구 입력 칸과 글자 수. 다 지워도 상자가 사라지지 않도록 빈 문구는 캔버스에 반영하지 않고,
 * 칸을 벗어나면 마지막 문구로 되돌린다.
 *
 * @param props - 지금 문구, 변경 처리 함수
 * @returns 문구 입력 묶음
 */
function TextInput({ value, onChange }: TextInputProps) {
  const [draft, setDraft] = useState(value);
  const { max } = LAYER_LIMITS.textLength;

  // 캔버스에서 직접 입력하면 따라간다
  useEffect(() => {
    setDraft(value);
  }, [value]);

  return (
    <div className={styles.field}>
      <div className={styles.labelRow}>
        <label className={styles.label} htmlFor="text-layer-text">
          문구
        </label>
        <span className={styles.count}>
          {draft.length}/{max}
        </span>
      </div>
      <textarea
        id="text-layer-text"
        className={styles.textarea}
        rows={2}
        maxLength={max}
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value);
          if (e.target.value.trim() !== "") onChange(e.target.value);
        }}
        onBlur={() => setDraft(value)}
      />
    </div>
  );
}

interface ToggleButtonProps {
  label: string;
  pressed: boolean;
  onClick: () => void;
  children: ReactNode;
}

/**
 * 글자 모양·정렬 토글 버튼.
 *
 * @param props - 이름, 눌림 여부, 클릭 처리 함수, 아이콘
 * @returns 토글 버튼
 */
function ToggleButton({ label, pressed, onClick, children }: ToggleButtonProps) {
  return (
    <button
      type="button"
      className={styles.toggle}
      title={label}
      aria-label={label}
      aria-pressed={pressed}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

/**
 * [+ 텍스트 상자 추가] 버튼과, 선택한 문구 상자의 문구·글꼴·크기·모양·색·효과·위치 조절,
 * [삭제] 버튼을 보여준다. 크기와 위치는 원본 이미지 기준 px로 보여주고, 저장은 비율로 한다.
 *
 * @param props - 선택한 문구 상자, 이미지 크기, 안내 문구, 추가·삭제·변경 처리 함수
 * @returns 문구 패널
 */
export default function TextLayerPanel({
  selectedLayer,
  imageWidth,
  imageHeight,
  notice,
  onAdd,
  onDelete,
  onChange,
  onFontPreview,
}: TextLayerPanelProps) {
  const limits = LAYER_LIMITS;

  return (
    <section className={styles.section} aria-label="텍스트 편집기">
      <Button variant="primary" icon={<Plus size={14} />} onClick={onAdd}>
        텍스트 상자 추가
      </Button>

      {selectedLayer ? (
        <>
          <TextInput
            key={`text-${selectedLayer.id}`}
            value={selectedLayer.text}
            onChange={(text) => onChange(selectedLayer.id, { text })}
          />

          <div className={styles.field}>
            <span className={styles.label}>글꼴</span>
            <FontPicker
              value={selectedLayer.fontId}
              onChange={(fontId) => onChange(selectedLayer.id, { fontId })}
              onPreview={onFontPreview}
            />
          </div>

          <div className={styles.pair}>
            <div className={styles.field}>
              <span className={styles.label}>글자 모양</span>
              <div className={styles.toggles}>
                <ToggleButton
                  label="굵게"
                  pressed={selectedLayer.bold}
                  onClick={() => onChange(selectedLayer.id, { bold: !selectedLayer.bold })}
                >
                  <Bold size={16} />
                </ToggleButton>
                <ToggleButton
                  label="기울임"
                  pressed={selectedLayer.italic}
                  onClick={() => onChange(selectedLayer.id, { italic: !selectedLayer.italic })}
                >
                  <Italic size={16} />
                </ToggleButton>
                <ToggleButton
                  label="취소선"
                  pressed={selectedLayer.strike}
                  onClick={() => onChange(selectedLayer.id, { strike: !selectedLayer.strike })}
                >
                  <Strikethrough size={16} />
                </ToggleButton>
              </div>
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="text-layer-font-size">
                크기
              </label>
              <NumberField
                id="text-layer-font-size"
                label="글자 크기"
                buttonStep={FONT_SIZE_BUTTON_STEP_PX}
                value={Math.round(selectedLayer.fontSize * imageHeight)}
                min={Math.ceil(limits.fontSize.min * imageHeight)}
                max={Math.floor(limits.fontSize.max * imageHeight)}
                onChange={(px) => onChange(selectedLayer.id, { fontSize: px / imageHeight })}
              />
            </div>
          </div>

          <div className={styles.pair}>
            <div className={styles.field}>
              <span className={styles.label}>정렬</span>
              <div className={styles.toggles}>
                {ALIGN_OPTIONS.map(({ value, label, icon }) => (
                  <ToggleButton
                    key={value}
                    label={label}
                    pressed={selectedLayer.align === value}
                    onClick={() => onChange(selectedLayer.id, { align: value })}
                  >
                    {icon}
                  </ToggleButton>
                ))}
              </div>
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="text-layer-line-height">
                줄 간격
              </label>
              <NumberField
                id="text-layer-line-height"
                label="줄 간격"
                step={LINE_HEIGHT_BUTTON_STEP}
                buttonStep={LINE_HEIGHT_BUTTON_STEP}
                value={Number(selectedLayer.lineHeight.toFixed(2))}
                min={limits.lineHeight.min}
                max={limits.lineHeight.max}
                onChange={(lineHeight) => onChange(selectedLayer.id, { lineHeight })}
              />
            </div>
          </div>

          <div className={styles.field}>
            <span className={styles.label}>색</span>
            <ColorField
              label="글자색"
              value={selectedLayer.color}
              opacity={selectedLayer.opacity}
              onChange={(color) => onChange(selectedLayer.id, { color })}
              onOpacityChange={(opacity) => onChange(selectedLayer.id, { opacity })}
            />
          </div>

          <TextEffectFields
            key={`effects-${selectedLayer.id}`}
            layer={selectedLayer}
            imageHeight={imageHeight}
            onChange={(changes) => onChange(selectedLayer.id, changes)}
          />

          <div className={styles.field}>
            <span className={styles.label}>위치</span>
            <div className={styles.position}>
              <label className={styles.axis}>
                X
                <NumberField
                  value={Math.round(selectedLayer.x * imageWidth)}
                  min={0}
                  max={imageWidth}
                  onChange={(px) => onChange(selectedLayer.id, { x: px / imageWidth })}
                />
              </label>
              <label className={styles.axis}>
                Y
                <NumberField
                  value={Math.round(selectedLayer.y * imageHeight)}
                  min={0}
                  max={imageHeight}
                  onChange={(px) => onChange(selectedLayer.id, { y: px / imageHeight })}
                />
              </label>
            </div>
          </div>

          <SliderField
            label="회전"
            unit="°"
            value={Math.round(selectedLayer.rotation)}
            min={limits.rotation.min}
            max={limits.rotation.max}
            onChange={(rotation) => onChange(selectedLayer.id, { rotation })}
          />

          <Button
            className={styles.deleteButton}
            icon={<Trash2 size={14} />}
            onClick={() => onDelete(selectedLayer.id)}
          >
            선택한 상자 삭제
          </Button>
        </>
      ) : (
        <p className={styles.hint}>상자를 누르면 문구와 모양을 바꿀 수 있어요</p>
      )}

      {notice && <p className={styles.notice}>{notice}</p>}
    </section>
  );
}
