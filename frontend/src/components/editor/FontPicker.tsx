/**
 * 문구 글꼴을 고르는 메뉴 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
 * 수정자: bioyejin
 */

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { Check, ChevronDown } from "lucide-react";
import {
  AD_FONTS,
  FONT_CATEGORY_LABELS,
  toFontFamily,
  type AdFont,
  type AdFontCategory,
} from "../../constants/fonts";
import { findFont } from "./textLayer";
import styles from "./FontPicker.module.css";

export interface FontPickerProps {
  /** 고른 글꼴 id */
  value: string;
  onChange: (fontId: string) => void;
  /** 목록의 항목으로 이동하면 그 글꼴 id, 벗어나거나 고르지 않고 닫으면 null로 호출 (캔버스 임시 미리보기) */
  onPreview: (fontId: string | null) => void;
}

// 분류 표시 순서 (FONT_CATEGORY_LABELS에 적힌 순서)
const CATEGORIES = Object.keys(FONT_CATEGORY_LABELS) as AdFontCategory[];

interface FontOptionProps {
  font: AdFont;
  selected: boolean;
  /** 목록 스크롤 영역. 이 안에 보일 때만 글꼴 파일을 받는다 */
  root: HTMLElement | null;
  onSelect: (fontId: string) => void;
  /** 키보드로 이 항목에 오거나 마우스를 올렸을 때 호출 */
  onPreview: (fontId: string) => void;
}

/**
 * 글꼴 이름을 그 글꼴로 보여주는 목록 항목.
 * 29종을 한꺼번에 받지 않도록, 목록에서 화면에 보일 때만 그 글꼴을 적용한다(그때 파일을 받음).
 *
 * @param props - 글꼴, 선택 여부, 스크롤 영역, 고르기·미리보기 처리 함수
 * @returns 목록 항목
 */
function FontOption({ font, selected, root, onSelect, onPreview }: FontOptionProps) {
  const ref = useRef<HTMLButtonElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element || visible) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) setVisible(true);
      },
      { root },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [root, visible]);

  return (
    <button
      ref={ref}
      type="button"
      role="option"
      aria-selected={selected}
      className={`${styles.option} ${selected ? styles.selected : ""}`}
      style={visible ? { fontFamily: toFontFamily(font) } : undefined}
      title={font.mood}
      onFocus={() => onPreview(font.id)}
      onMouseEnter={() => onPreview(font.id)}
      onClick={() => onSelect(font.id)}
    >
      <span className={styles.optionName}>{font.name}</span>
      {selected && <Check size={14} aria-hidden="true" />}
    </button>
  );
}

/**
 * 고른 글꼴 이름을 그 글꼴로 보여주는 버튼. 누르면 분류별로 묶인 글꼴 목록이 열린다.
 * ↑/↓ 키로 옮겨 다니거나 마우스를 올리면 캔버스에 그 글꼴이 임시로 보이고, Enter나 클릭으로 확정한다.
 * 마우스가 목록을 벗어나거나, 고르지 않고 Esc나 바깥 클릭으로 닫으면 원래 글꼴로 돌아간다.
 *
 * @param props - 고른 글꼴 id, 고르기·미리보기 처리 함수
 * @returns 글꼴 메뉴
 */
export default function FontPicker({ value, onChange, onPreview }: FontPickerProps) {
  const [open, setOpen] = useState(false);
  const [list, setList] = useState<HTMLDivElement | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listId = useId();
  const current = findFont(value);

  /** 고르지 않고 메뉴를 닫는다. 임시 미리보기도 함께 지운다. */
  function close() {
    setOpen(false);
    onPreview(null);
  }

  // 열려 있는 동안 바깥을 누르면 닫는다
  useEffect(() => {
    if (!open) return;
    function handlePointerDown(e: PointerEvent) {
      if (rootRef.current?.contains(e.target as Node)) return;
      setOpen(false);
      onPreview(null);
    }
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open, onPreview]);

  // 열리면 고른 글꼴을 보이게 하고 포커스를 옮긴다
  useEffect(() => {
    if (!open || !list) return;
    const selected = list.querySelector<HTMLButtonElement>('[aria-selected="true"]');
    selected?.scrollIntoView({ block: "center" });
    selected?.focus();
  }, [open, list]);

  /** 글꼴을 고르고 메뉴를 닫는다. */
  function handleSelect(fontId: string) {
    onChange(fontId);
    close();
    buttonRef.current?.focus();
  }

  /** Esc로 닫고, ↑/↓로 앞뒤 항목에 포커스를 옮긴다. */
  function handleListKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Escape") {
      e.preventDefault();
      close();
      buttonRef.current?.focus();
      return;
    }
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const options = Array.from(
      e.currentTarget.querySelectorAll<HTMLButtonElement>("[role=option]"),
    );
    const index = options.indexOf(document.activeElement as HTMLButtonElement);
    const next = e.key === "ArrowDown" ? index + 1 : index - 1;
    options[Math.min(options.length - 1, Math.max(0, next))]?.focus();
  }

  return (
    <div ref={rootRef} className={styles.root}>
      <button
        ref={buttonRef}
        type="button"
        className={styles.trigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        style={{ fontFamily: toFontFamily(current) }}
        onClick={() => (open ? close() : setOpen(true))}
      >
        <span className={styles.optionName}>{current.name}</span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>

      {open && (
        <div
          ref={setList}
          id={listId}
          role="listbox"
          aria-label="글꼴"
          className={styles.list}
          onKeyDown={handleListKeyDown}
          onMouseLeave={() => onPreview(null)}
        >
          {CATEGORIES.map((category) => {
            const fonts = AD_FONTS.filter((font) => font.category === category);
            if (fonts.length === 0) return null;
            return (
              <div key={category} role="group" aria-label={FONT_CATEGORY_LABELS[category]}>
                <p className={styles.category}>{FONT_CATEGORY_LABELS[category]}</p>
                {fonts.map((font) => (
                  <FontOption
                    key={font.id}
                    font={font}
                    selected={font.id === current.id}
                    root={list}
                    onSelect={handleSelect}
                    onPreview={onPreview}
                  />
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
