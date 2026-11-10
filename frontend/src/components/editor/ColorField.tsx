/**
 * 색 동그라미와 hex 입력 칸으로 색을 고르는 컴포넌트.
 *
 * 생성일자: 2026-11-05
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { useContext, useEffect, useId, useState } from "react";
import { TEXT_COLOR_PRESETS } from "../../constants/editor";
import { ImagePaletteContext } from "./imagePalette";
import SliderField from "./SliderField";
import { HEX_COLOR } from "./textLayer";
import styles from "./ColorField.module.css";

export interface ColorFieldProps {
  /** 스크린리더에 알려줄 이름 (예: 글자색) */
  label: string;
  /** 지금 색 (#RRGGBB) */
  value: string;
  /** 지금 불투명도 (0~1) */
  opacity: number;
  onChange: (color: string) => void;
  onOpacityChange: (opacity: number) => void;
}

/**
 * 색 동그라미와 hex 입력 칸, 그 아래 불투명도 슬라이더를 보여준다. 동그라미를 누르면 사이에
 * 1줄 기본색(무지개 원 = 브라우저 색상 선택기, 스포이드 포함)과 2줄 이미지 색(편집 중인 이미지의
 * 대표색, ImagePaletteContext)이 펼쳐진다. hex는 #RRGGBB가 완성되면
 * 바로 반영하고, 칸을 벗어날 때 틀린 값이면 원래 색으로 되돌린다.
 *
 * @param props - 이름, 지금 색과 불투명도, 변경 처리 함수
 * @returns 색 선택 묶음
 */
export default function ColorField({
  label,
  value,
  opacity,
  onChange,
  onOpacityChange,
}: ColorFieldProps) {
  const imageColors = useContext(ImagePaletteContext);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(value);
  const paletteId = useId();

  // 팔레트나 캔버스 쪽에서 색이 바뀌면 따라간다
  useEffect(() => {
    setDraft(value);
  }, [value]);

  /**
   * 입력한 hex 값을 받아, 완성된 색이면 바로 반영한다.
   *
   * @param input - 입력 칸의 값 (# 없이 쳐도 된다)
   */
  function handleHexChange(input: string) {
    const hex = input.startsWith("#") ? input : `#${input}`;
    setDraft(input);
    if (HEX_COLOR.test(hex)) onChange(hex.toUpperCase());
  }

  return (
    <div className={styles.root}>
      <div className={styles.row}>
        <button
          type="button"
          className={styles.current}
          style={{ background: value }}
          aria-label={`${label} 고르기`}
          aria-expanded={open}
          aria-controls={paletteId}
          onClick={() => setOpen((prev) => !prev)}
        />
        <input
          type="text"
          className={styles.hex}
          value={draft}
          maxLength={7}
          spellCheck={false}
          aria-label={`${label} hex 값`}
          onChange={(e) => handleHexChange(e.target.value)}
          onBlur={() => setDraft(value)}
        />
      </div>

      {open && (
        <div id={paletteId} className={styles.palette}>
          <div className={styles.paletteRow} role="group" aria-label={`${label} 기본색`}>
            <span className={styles.rowLabel}>기본색</span>
            <div className={styles.swatches}>
              {/* 무지개색 원을 눌러 브라우저 색상 선택기(스포이드 포함)를 연다 */}
              <label className={styles.picker} title="다른 색 고르기">
                <input
                  type="color"
                  className={styles.pickerInput}
                  value={value.toLowerCase()}
                  aria-label="다른 색 고르기"
                  onChange={(e) => onChange(e.target.value.toUpperCase())}
                />
              </label>
              {TEXT_COLOR_PRESETS.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  className={styles.swatch}
                  style={{ background: preset.value }}
                  aria-label={preset.label}
                  aria-pressed={value === preset.value}
                  onClick={() => onChange(preset.value)}
                />
              ))}
            </div>
          </div>

          {/* 이미지에서 뽑은 대표색. 계산 중이거나 뽑지 못했으면 줄을 숨긴다 */}
          {imageColors.length > 0 && (
            <div className={styles.paletteRow} role="group" aria-label={`${label} 이미지 색`}>
              <span className={styles.rowLabel}>이미지 색</span>
              <div className={styles.swatches}>
                {imageColors.map((color) => (
                  <button
                    key={color}
                    type="button"
                    className={styles.swatch}
                    style={{ background: color }}
                    title={color}
                    aria-label={`이미지 색 ${color}`}
                    aria-pressed={value === color}
                    onClick={() => onChange(color)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <SliderField
        label="불투명도"
        unit="%"
        value={Math.round(opacity * 100)}
        min={0}
        max={100}
        onChange={(percent) => onOpacityChange(percent / 100)}
      />
    </div>
  );
}
