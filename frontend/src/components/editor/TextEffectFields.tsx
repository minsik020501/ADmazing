/**
 * 외곽선·그림자·배경 상자를 켜고 조절하는 [효과] 패널 묶음 컴포넌트.
 *
 * 생성일자: 2026-11-05
 * 생성자: bioyejin
 * 수정일자: 2026-11-05
 * 수정자: bioyejin
 */

import { useRef, useState, type ReactNode } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import {
  DEFAULT_BACKGROUND,
  DEFAULT_SHADOW,
  DEFAULT_STROKE,
  EFFECT_MAX_PX,
  LAYER_LIMITS,
} from "../../constants/editor";
import ColorField from "./ColorField";
import SliderField from "./SliderField";
import type { StrokeJoin, TextLayer, TextShadow } from "./textLayer";
import styles from "./TextEffectFields.module.css";

const STROKE_JOINS: { value: StrokeJoin; label: string }[] = [
  { value: "miter", label: "각지게" },
  { value: "round", label: "둥글게" },
];

// 슬라이더 끝이 0°와 겹치지 않게 359°까지 쓴다
const MAX_SHADOW_ANGLE = 359;

interface EffectRowProps {
  title: string;
  /** 켜져 있으면 true */
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  /** 펼쳤을 때 보이는 세부 조절 */
  children: ReactNode;
}

/**
 * 효과 하나. 왼쪽 스위치로 켜고 끄며, 켜면 세부 조절이 바로 펼쳐진다.
 * 켜져 있는 동안 오른쪽 화살표로 접고 펼 수 있고, 꺼져 있으면 화살표를 숨긴다.
 *
 * @param props - 이름, 켜짐 여부, 스위치 처리 함수, 세부 조절
 * @returns 효과 한 줄
 */
function EffectRow({ title, enabled, onToggle, children }: EffectRowProps) {
  const [expanded, setExpanded] = useState(false);
  const open = enabled && expanded;

  return (
    <div className={styles.effect}>
      <div className={styles.header}>
        <label className={styles.toggle}>
          <input
            type="checkbox"
            role="switch"
            className={styles.switch}
            checked={enabled}
            onChange={(e) => {
              setExpanded(e.target.checked);
              onToggle(e.target.checked);
            }}
          />
          {title}
        </label>
        {enabled && (
          <button
            type="button"
            className={styles.expand}
            aria-label={`${title} 세부 옵션 ${open ? "접기" : "펼치기"}`}
            aria-expanded={open}
            onClick={() => setExpanded((prev) => !prev)}
          >
            {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        )}
      </div>
      {/* 높이가 자연스럽게 늘고 줄도록 칸은 항상 두고, 접혔을 때 높이만 0으로 만든다 */}
      <div className={`${styles.slide} ${open ? styles.open : ""}`}>
        <div className={styles.body}>{children}</div>
      </div>
    </div>
  );
}

/**
 * 그림자 위치(가로·세로)를 각도와 거리로 바꾼다.
 *
 * @param shadow - 그림자 값
 * @returns 각도(도, 0이 오른쪽이고 시계 방향이 +)와 거리(이미지 세로 대비 비율)
 */
function toShadowPolar({ offsetX, offsetY }: TextShadow): { angle: number; distance: number } {
  const degrees = Math.round((Math.atan2(offsetY, offsetX) * 180) / Math.PI);
  return { angle: (degrees + 360) % 360, distance: Math.hypot(offsetX, offsetY) };
}

/**
 * 각도와 거리를 그림자 위치(가로·세로)로 바꾼다.
 *
 * @param angle - 각도(도)
 * @param distance - 거리 (이미지 세로 대비 비율)
 * @returns 그림자 위치
 */
function fromShadowPolar(angle: number, distance: number): Pick<TextShadow, "offsetX" | "offsetY"> {
  const radians = (angle * Math.PI) / 180;
  return { offsetX: distance * Math.cos(radians), offsetY: distance * Math.sin(radians) };
}

export interface TextEffectFieldsProps {
  layer: TextLayer;
  /** 원본 이미지 세로(px). 효과 크기를 px로 보여주는 데 쓴다 */
  imageHeight: number;
  onChange: (changes: Partial<Omit<TextLayer, "id">>) => void;
}

/**
 * [효과] 묶음. 두께·흐림·거리·여백은 원본 이미지 기준 px로 보여주고, 저장은 이미지 세로 대비
 * 비율로 한다. 껐다가 다시 켜면 끄기 전 값으로 돌아온다 (상자가 바뀌면 key로 새로 만들어 비운다).
 *
 * @param props - 문구 상자, 이미지 세로, 변경 처리 함수
 * @returns 효과 조절 묶음
 */
export default function TextEffectFields({ layer, imageHeight, onChange }: TextEffectFieldsProps) {
  const { stroke, shadow, background } = layer;
  const limits = LAYER_LIMITS;
  // 끄기 직전 값
  const lastRef = useRef({ stroke, shadow, background });
  const shadowPolar = shadow && toShadowPolar(shadow);

  /** 비율을 화면에 보여줄 px로 바꾼다. */
  const toPx = (ratio: number) => Math.round(ratio * imageHeight);

  return (
    <div className={styles.group}>
      <span className={styles.heading}>효과</span>

      <EffectRow
        title="외곽선"
        enabled={stroke !== null}
        onToggle={(on) => {
          if (stroke) lastRef.current.stroke = stroke;
          onChange({ stroke: on ? (lastRef.current.stroke ?? { ...DEFAULT_STROKE }) : null });
        }}
      >
        {stroke && (
          <>
            <ColorField
              label="외곽선 색"
              value={stroke.color}
              opacity={stroke.opacity}
              onChange={(color) => onChange({ stroke: { ...stroke, color } })}
              onOpacityChange={(opacity) => onChange({ stroke: { ...stroke, opacity } })}
            />
            <SliderField
              label="두께"
              unit="px"
              value={toPx(stroke.width)}
              min={toPx(limits.strokeWidth.min)}
              max={EFFECT_MAX_PX.strokeWidth}
              onChange={(px) => onChange({ stroke: { ...stroke, width: px / imageHeight } })}
            />
            <div className={styles.joinRow}>
              <span className={styles.joinLabel}>모서리</span>
              <div className={styles.segment} role="group" aria-label="외곽선 모서리">
                {STROKE_JOINS.map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    className={styles.segmentButton}
                    aria-pressed={stroke.join === value}
                    onClick={() => onChange({ stroke: { ...stroke, join: value } })}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </EffectRow>

      <EffectRow
        title="그림자"
        enabled={shadow !== null}
        onToggle={(on) => {
          if (shadow) lastRef.current.shadow = shadow;
          onChange({ shadow: on ? (lastRef.current.shadow ?? { ...DEFAULT_SHADOW }) : null });
        }}
      >
        {shadow && shadowPolar && (
          <>
            <ColorField
              label="그림자 색"
              value={shadow.color}
              opacity={shadow.opacity}
              onChange={(color) => onChange({ shadow: { ...shadow, color } })}
              onOpacityChange={(opacity) => onChange({ shadow: { ...shadow, opacity } })}
            />
            <SliderField
              label="각도"
              unit="°"
              value={shadowPolar.angle}
              min={0}
              max={MAX_SHADOW_ANGLE}
              onChange={(angle) =>
                onChange({
                  shadow: { ...shadow, ...fromShadowPolar(angle, shadowPolar.distance) },
                })
              }
            />
            <SliderField
              label="거리"
              unit="px"
              value={toPx(shadowPolar.distance)}
              min={0}
              max={EFFECT_MAX_PX.shadowDistance}
              onChange={(px) =>
                onChange({
                  shadow: { ...shadow, ...fromShadowPolar(shadowPolar.angle, px / imageHeight) },
                })
              }
            />
            <SliderField
              label="흐림"
              unit="px"
              value={toPx(shadow.blur)}
              min={toPx(limits.shadowBlur.min)}
              max={EFFECT_MAX_PX.shadowBlur}
              onChange={(px) => onChange({ shadow: { ...shadow, blur: px / imageHeight } })}
            />
          </>
        )}
      </EffectRow>

      <EffectRow
        title="배경 상자"
        enabled={background !== null}
        onToggle={(on) => {
          if (background) lastRef.current.background = background;
          onChange({
            background: on ? (lastRef.current.background ?? { ...DEFAULT_BACKGROUND }) : null,
          });
        }}
      >
        {background && (
          <>
            <ColorField
              label="배경 상자 색"
              value={background.color}
              opacity={background.opacity}
              onChange={(color) => onChange({ background: { ...background, color } })}
              onOpacityChange={(opacity) => onChange({ background: { ...background, opacity } })}
            />
            <SliderField
              label="여백"
              unit="px"
              value={toPx(background.padding)}
              min={toPx(limits.backgroundPadding.min)}
              max={EFFECT_MAX_PX.backgroundPadding}
              onChange={(px) =>
                onChange({ background: { ...background, padding: px / imageHeight } })
              }
            />
            <SliderField
              label="모서리"
              unit="px"
              value={toPx(background.radius)}
              min={toPx(limits.backgroundRadius.min)}
              max={toPx(limits.backgroundRadius.max)}
              onChange={(px) =>
                onChange({ background: { ...background, radius: px / imageHeight } })
              }
            />
          </>
        )}
      </EffectRow>
    </div>
  );
}
