/**
 * 에디터 AI 추천 탭의 추천안(칩) 목록과 레이아웃·스타일 선택 컴포넌트.
 *
 * 생성일자: 2026-11-10
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import type { ReactNode } from "react";
import type { ImageCopies } from "../../api/client";
import {
  CHIP_TITLE_LENGTH,
  FONT_STYLES,
  LAYOUT_TEMPLATES,
  NARROW_PANEL_MESSAGE,
  isNarrowPanel,
} from "../../constants/layoutOptions";
import { chipCount, type LayoutChoice, type ProposalState } from "../../hooks/useCopyProposals";
import type { AppliedProposal } from "../../hooks/useTextLayers";
import Chip from "../common/Chip";
import LayoutIcon from "./LayoutIcon";
import styles from "./AiProposalList.module.css";

export interface AiProposalListProps {
  /** 이미지의 추천 문구. 추천에 실패했으면 null */
  copies: ImageCopies | null;
  /** 문구 추천에 실패했을 때 서버가 보낸 메시지 */
  copiesError: string | null;
  /** 이미지 비율 (좁은 패널 안내에 쓴다) */
  ratio: string;
  /** 이 이미지의 추천안 상태 */
  state: ProposalState;
  /** 배치를 받아 오는 중이면 true */
  busy: boolean;
  /** 추천안 칩을 누를 때 호출 */
  onApply: (chipIndex: number) => void;
  /** 레이아웃·스타일 칩을 누를 때 호출 */
  onChoose: (choice: LayoutChoice) => void;
}

/**
 * 칩에 보여줄 Title. CHIP_TITLE_LENGTH 글자를 넘으면 뒤를 …으로 줄인다.
 *
 * @param title - Title 문구
 * @returns 줄인 Title
 */
function shortTitle(title: string): string {
  // 이모지처럼 두 칸을 쓰는 글자가 잘리지 않게 글자 단위로 센다
  const chars = Array.from(title);
  return chars.length > CHIP_TITLE_LENGTH
    ? `${chars.slice(0, CHIP_TITLE_LENGTH).join("").trimEnd()}…`
    : title;
}

interface OptionProps {
  /** 마우스를 올리면 보여줄 이름 */
  label: string;
  selected: boolean;
  recommended: boolean;
  disabled: boolean;
  onClick: () => void;
  children: ReactNode;
}

/**
 * 레이아웃·스타일 칩 하나. 추천 항목에는 오른쪽 위에 '추천' 배지를 붙인다.
 *
 * @param props - 이름, 선택·추천·비활성 여부, 클릭 처리, 칩 내용
 * @returns 칩
 */
function Option({ label, selected, recommended, disabled, onClick, children }: OptionProps) {
  return (
    <span className={styles.option} title={label}>
      <Chip selected={selected} disabled={disabled} onClick={onClick}>
        {children}
      </Chip>
      {recommended && <span className={styles.badge}>추천</span>}
    </span>
  );
}

interface ChoicesProps {
  /** 이 칩이 적용된 칩이면 지금 레이아웃·스타일. 아니면 null (접혀 있다) */
  applied: AppliedProposal | null;
  ratio: string;
  recommendedTemplateId: string | null;
  recommendedStyleId: string | null;
  disabled: boolean;
  onChoose: (choice: LayoutChoice) => void;
}

/**
 * 적용한 칩 밑에 펼쳐지는 레이아웃(위치 아이콘, 한 줄 스크롤)과 스타일(글자) 선택.
 *
 * @param props - 지금 조합, 비율, 추천 항목, 비활성 여부, 조합 변경 함수
 * @returns 레이아웃·스타일 선택 영역
 */
function Choices({
  applied,
  ratio,
  recommendedTemplateId,
  recommendedStyleId,
  disabled,
  onChoose,
}: ChoicesProps) {
  return (
    <div className={styles.choices}>
      <div className={styles.group} role="group" aria-label="레이아웃">
        <span className={styles.groupLabel}>레이아웃</span>
        <div className={styles.scrollRow}>
          {LAYOUT_TEMPLATES.map((option) => (
            <Option
              key={option.id}
              label={option.label}
              selected={applied?.templateId === option.id}
              recommended={recommendedTemplateId === option.id}
              disabled={disabled}
              onClick={() => onChoose({ templateId: option.id })}
            >
              <LayoutIcon templateId={option.id} />
              <span className={styles.srOnly}>{option.label}</span>
            </Option>
          ))}
        </div>
      </div>

      <div className={styles.group} role="group" aria-label="스타일">
        <span className={styles.groupLabel}>스타일</span>
        <div className={styles.scrollRow}>
          {FONT_STYLES.map((option) => (
            <Option
              key={option.id}
              label={option.label}
              selected={applied?.styleId === option.id}
              recommended={recommendedStyleId === option.id}
              disabled={disabled}
              onClick={() => onChoose({ styleId: option.id })}
            >
              {option.label}
            </Option>
          ))}
        </div>
      </div>

      {applied && isNarrowPanel(applied.templateId, ratio) && (
        <p className={styles.warning}>{NARROW_PANEL_MESSAGE}</p>
      )}
    </div>
  );
}

/**
 * 추천 문구 묶음을 한 줄 칩("추천안 1 ✨" + 줄인 Title)으로 보여준다. 칩을 누르면 이미지에 문구가
 * 들어가고, 그 칩 밑에 레이아웃(위치 아이콘)과 스타일(글자) 선택이 슬라이드로 펼쳐진다.
 * 배치를 받아 오는 동안의 "적용 중..." 표시는 캔버스 쪽(EditorPage)에서 한다.
 *
 * @param props - 추천 문구, 실패 메시지, 비율, 추천안 상태, 칩 적용·조합 변경 함수
 * @returns 추천안 목록
 */
export default function AiProposalList({
  copies,
  copiesError,
  ratio,
  state,
  busy,
  onApply,
  onChoose,
}: AiProposalListProps) {
  const count = copies ? chipCount(copies) : 0;
  const { applied } = state;

  if (!copies || count === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.emptyMessage}>{copiesError ?? "이 이미지에는 추천 문구가 없어요"}</p>
        <p className={styles.hint}>텍스트 편집기 탭에서 문구를 직접 추가할 수 있어요</p>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      <p className={styles.hint}>추천안을 누르면 이미지에 문구가 들어가요</p>

      <ul className={styles.chips}>
        {Array.from({ length: count }, (_, i) => {
          const open = applied?.chipIndex === i;
          return (
            <li key={i}>
              <button
                type="button"
                className={`${styles.chip} ${open ? styles.selected : ""}`}
                aria-pressed={open}
                aria-busy={state.pendingChip === i}
                aria-expanded={open}
                disabled={busy}
                onClick={() => onApply(i)}
              >
                <span className={styles.number}>추천안 {i + 1} ✨</span>
                <strong className={styles.title}>{shortTitle(copies.title[i].text)}</strong>
              </button>

              {/* 접혀 있어도 그려 두어야 펼칠 때·접을 때 모두 슬라이드가 보인다 */}
              <div className={`${styles.slide} ${open ? styles.slideOpen : ""}`}>
                <div className={styles.slideInner}>
                  <Choices
                    applied={open ? applied : null}
                    ratio={ratio}
                    recommendedTemplateId={open ? state.recommendedTemplateId : null}
                    recommendedStyleId={state.recommendedStyleId}
                    disabled={busy || !open}
                    onChoose={onChoose}
                  />
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      {state.error && (
        <p className={styles.error} role="alert">
          {state.error}
        </p>
      )}
    </div>
  );
}
