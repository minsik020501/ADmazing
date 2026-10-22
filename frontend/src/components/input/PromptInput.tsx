/**
 * 프롬프트 입력 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import { useId, type FormEvent, type KeyboardEvent } from "react";
import Button from "../common/Button";
import styles from "./PromptInput.module.css";

/** Mac에서는 Ctrl 대신 ⌘(Command) 키를 안내한다 */
const SHORTCUT_LABEL = /Mac|iPhone|iPad/.test(navigator.userAgent) ? "⌘ + Enter" : "Ctrl + Enter";

export interface PromptInputProps {
  /** 입력한 프롬프트. 값은 App이 보관한다(새로 만들기 시 초기화 등) */
  value: string;
  onChange: (value: string) => void;
  /** 생성 버튼 또는 단축키로 생성을 요청할 때 호출 */
  onSubmit: () => void;
  /** 생성 중이면 버튼을 비활성화하고 "생성 중..."을 표시 */
  loading: boolean;
}

/**
 * 번호 라벨, 입력창, 안내·예시 문구, 글자 수, 생성 버튼으로 된 프롬프트 입력 영역.
 * 입력창에서 Ctrl+Enter(Mac은 ⌘+Enter)로도 생성할 수 있다.
 *
 * @param props - 입력값, 변경·생성 처리 함수, 생성 중 여부
 * @returns 프롬프트 입력 폼
 */
export default function PromptInput({ value, onChange, onSubmit, loading }: PromptInputProps) {
  const inputId = useId();
  const canSubmit = value.trim().length > 0 && !loading;

  /** 폼 제출(생성 버튼)을 처리한다. */
  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (canSubmit) onSubmit();
  }

  /** Ctrl+Enter / ⌘+Enter로 생성한다. */
  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      if (canSubmit) onSubmit();
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <label className={styles.label} htmlFor={inputId}>
        1. 프롬프트
      </label>
      <textarea
        id={inputId}
        className={styles.textarea}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="만들고 싶은 광고 이미지를 자유롭게 설명해 주세요"
        rows={4}
      />

      <div className={styles.meta}>
        <div className={styles.hints}>
          <p>색감·분위기·구도를 구체적으로 적을수록 좋아요</p>
          <p>ex. 나무 테이블 위의 라떼, 따뜻한 조명, 아늑한 카페 분위기, 위에서 내려다본 구도</p>
        </div>
        <span className={styles.count}>{value.length}자</span>
      </div>

      <div className={styles.actions}>
        <Button type="submit" variant="primary" disabled={!canSubmit} title={SHORTCUT_LABEL}>
          {loading ? "생성 중..." : "이미지 생성"}
        </Button>
      </div>
    </form>
  );
}
