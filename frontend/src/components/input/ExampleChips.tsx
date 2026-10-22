/**
 * 예시 프롬프트 칩 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import { useCallback, useId, useState } from "react";
import { EXAMPLE_PROMPTS, type ExamplePrompt } from "../../constants/examplePrompts";
import Chip from "../common/Chip";
import Modal from "../common/Modal";
import styles from "./ExampleChips.module.css";

export interface ExampleChipsProps {
  /** 지금 입력창에 있는 문구 */
  value: string;
  /** 예시 문장으로 입력창을 채울 때 호출 */
  onSelect: (prompt: string) => void;
}

/**
 * 업종별 예시 프롬프트 칩 목록.
 * 입력창이 비어 있으면 바로 채우고, 글이 있으면 확인 팝업에서 [바꾸기]를 눌러야 바꾼다.
 *
 * @param props - 현재 입력 문구와 예시 선택 처리 함수
 * @returns 번호 라벨, 설명, 칩 목록과 확인 팝업
 */
export default function ExampleChips({ value, onSelect }: ExampleChipsProps) {
  const labelId = useId();
  // 확인 팝업에서 바꿀지 묻고 있는 예시. null이면 팝업 닫힘
  const [pending, setPending] = useState<ExamplePrompt | null>(null);

  /** 칩을 누르면 입력 상태에 따라 바로 채우거나 확인 팝업을 띄운다. */
  function handleClick(example: ExamplePrompt) {
    if (value === example.prompt) return;
    if (value.trim() === "") {
      onSelect(example.prompt);
      return;
    }
    setPending(example);
  }

  /** 확인 팝업에서 [바꾸기]를 누르면 입력창을 예시 문장으로 바꾼다. */
  function handleConfirm() {
    if (pending) onSelect(pending.prompt);
    setPending(null);
  }

  // 팝업이 다시 그려질 때마다 Esc 키 처리를 새로 걸지 않도록 같은 함수를 유지한다
  const handleCancel = useCallback(() => setPending(null), []);

  return (
    <section className={styles.section} aria-labelledby={labelId}>
      <h3 id={labelId} className={styles.label}>
        2. 예시 프롬프트
      </h3>
      <p className={styles.description}>누르면 입력창에 예시 문장이 채워져요</p>

      <div className={styles.chips}>
        {EXAMPLE_PROMPTS.map((example) => (
          <Chip key={example.id} onClick={() => handleClick(example)}>
            {example.label}
          </Chip>
        ))}
      </div>

      <Modal
        open={pending !== null}
        title="예시 문구로 바꿀까요?"
        confirmLabel="바꾸기"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      >
        지금 입력한 내용이 지워지고 <span className={styles.highlight}>{pending?.label}</span>{" "}
        예시로 바뀝니다.
      </Modal>
    </section>
  );
}
