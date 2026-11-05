/**
 * 에디터 오른쪽의 문구 패널 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
 * 수정자: bioyejin
 */

import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { LAYER_LIMITS, TEXT_COLOR_PRESETS } from "../../constants/editor";
import Button from "../common/Button";
import FontPicker from "./FontPicker";
import type { TextLayer } from "./textLayer";
import styles from "./TextLayerPanel.module.css";

export interface TextLayerPanelProps {
  /** 선택한 문구 상자. 없으면 null */
  selectedLayer: TextLayer | null;
  /** 원본 이미지 세로(px). 글자 크기를 px로 보여주는 데 쓴다 */
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

interface FontSizeInputProps {
  id: string;
  /** 지금 글자 크기(px) */
  value: number;
  min: number;
  max: number;
  /** 입력을 마쳤을 때 호출. 범위 안으로 맞춘 값을 돌려준다 */
  onCommit: (px: number) => number;
}

/**
 * 글자 크기 숫자 입력 칸. 입력하는 도중(예: "56"을 치려고 "5"만 친 상태)에 범위로 바뀌지 않도록
 * 칸 밖으로 나가거나 Enter를 누를 때 반영한다.
 *
 * @param props - 지금 값, 범위, 반영 처리 함수
 * @returns 숫자 입력 칸
 */
function FontSizeInput({ id, value, min, max, onCommit }: FontSizeInputProps) {
  const [draft, setDraft] = useState(String(value));

  // 슬라이더 등 다른 곳에서 크기가 바뀌면 따라간다
  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  /** 입력한 값을 반영한다. 숫자가 아니면 원래 값으로 되돌린다. */
  function commit() {
    const px = Number(draft);
    setDraft(String(draft.trim() !== "" && Number.isFinite(px) ? onCommit(px) : value));
  }

  return (
    <input
      id={id}
      type="number"
      className={styles.number}
      min={min}
      max={max}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
      }}
    />
  );
}

/**
 * [+ 텍스트 상자 추가] 버튼과, 선택한 문구 상자의 글꼴·크기·색 조절과 [삭제] 버튼을 보여준다.
 * 글자 크기는 원본 이미지 기준 px로 보여주고, 저장은 이미지 세로 대비 비율로 한다.
 *
 * @param props - 선택한 문구 상자, 이미지 세로, 안내 문구, 추가·삭제·변경 처리 함수
 * @returns 문구 패널
 */
export default function TextLayerPanel({
  selectedLayer,
  imageHeight,
  notice,
  onAdd,
  onDelete,
  onChange,
  onFontPreview,
}: TextLayerPanelProps) {
  const minSize = Math.ceil(LAYER_LIMITS.fontSize.min * imageHeight);
  const maxSize = Math.floor(LAYER_LIMITS.fontSize.max * imageHeight);

  /**
   * px 글자 크기를 범위 안으로 맞춰 비율로 저장한다.
   *
   * @param id - 문구 상자 id
   * @param px - 원본 이미지 기준 글자 크기
   * @returns 범위 안으로 맞춘 글자 크기(px)
   */
  function changeFontSize(id: string, px: number): number {
    const clamped = Math.round(Math.min(maxSize, Math.max(minSize, px)));
    onChange(id, { fontSize: clamped / imageHeight });
    return clamped;
  }

  return (
    <section className={styles.section} aria-label="텍스트 편집기">
      <Button variant="primary" icon={<Plus size={14} />} onClick={onAdd}>
        텍스트 상자 추가
      </Button>

      {selectedLayer ? (
        <>
          <div className={styles.field}>
            <span className={styles.label}>글꼴</span>
            <FontPicker
              value={selectedLayer.fontId}
              onChange={(fontId) => onChange(selectedLayer.id, { fontId })}
              onPreview={onFontPreview}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="text-layer-font-size">
              크기
            </label>
            <div className={styles.sizeRow}>
              <input
                type="range"
                className={styles.range}
                min={minSize}
                max={maxSize}
                value={Math.round(selectedLayer.fontSize * imageHeight)}
                aria-label="글자 크기 조절"
                onChange={(e) => changeFontSize(selectedLayer.id, Number(e.target.value))}
              />
              <FontSizeInput
                id="text-layer-font-size"
                value={Math.round(selectedLayer.fontSize * imageHeight)}
                min={minSize}
                max={maxSize}
                onCommit={(px) => changeFontSize(selectedLayer.id, px)}
              />
              <span className={styles.unit}>px</span>
            </div>
          </div>

          <div className={styles.field}>
            <span className={styles.label}>색</span>
            <div className={styles.colors} role="group" aria-label="글자색">
              {TEXT_COLOR_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  className={styles.swatch}
                  style={{ background: preset.value }}
                  aria-label={preset.label}
                  aria-pressed={selectedLayer.color === preset.value}
                  onClick={() => onChange(selectedLayer.id, { color: preset.value })}
                />
              ))}
              {/* 무지개색 원을 눌러 브라우저 색상 선택기(스포이드 포함)를 연다 */}
              <label className={styles.colorPicker} title="다른 색 고르기">
                <input
                  type="color"
                  className={styles.colorInput}
                  value={selectedLayer.color.toLowerCase()}
                  aria-label="다른 색 고르기"
                  onChange={(e) =>
                    onChange(selectedLayer.id, { color: e.target.value.toUpperCase() })
                  }
                />
              </label>
            </div>
          </div>

          <Button icon={<Trash2 size={14} />} onClick={() => onDelete(selectedLayer.id)}>
            선택한 상자 삭제
          </Button>
        </>
      ) : (
        <p className={styles.hint}>
          상자를 누르면 글꼴·크기·색을 바꿀 수 있어요. 두 번 누르면 문구를 고치고, 끌어서 옮길 수
          있어요
        </p>
      )}

      {notice && <p className={styles.notice}>{notice}</p>}
    </section>
  );
}
