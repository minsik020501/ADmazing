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
import SectionLabel from "../common/SectionLabel";
import styles from "./ExampleChips.module.css";

export interface ExampleChipsProps {
  /** 지금 입력창에 있는 문구 */
  value: string;
  /** 예시 문장으로 입력창을 채울 때 호출 */
  onSelect: (prompt: string) => void;
}

/** 모든 예시 문장. 입력창 내용이 손대지 않은 예시 문장인지 확인하는 데 쓴다 */
const ALL_EXAMPLE_PROMPTS = new Set(EXAMPLE_PROMPTS.flatMap((example) => example.prompts));

/** 확인 팝업에서 바꿀지 묻고 있는 예시 (칩 이름과 고른 문장) */
interface PendingExample {
  label: string;
  prompt: string;
}

/**
 * 업종의 예시 문장 중 하나를 무작위로 고른다. 지금 입력창에 있는 문장은 다시 고르지 않는다.
 *
 * @param example - 누른 칩의 업종별 예시
 * @param current - 지금 입력창에 있는 문구
 * @returns 입력창에 넣을 예시 문장
 */
function pickPrompt(example: ExamplePrompt, current: string): string {
  const candidates = example.prompts.filter((prompt) => prompt !== current);
  const pool = candidates.length > 0 ? candidates : example.prompts;
  return pool[Math.floor(Math.random() * pool.length)];
}

/**
 * 업종별 예시 프롬프트 칩 목록. 누를 때마다 그 업종의 문장 중 하나를 무작위로 채운다.
 * 입력창이 비어 있거나 예시 문장 그대로면 바로 채우고,
 * 직접 쓰거나 고친 글이 있으면 확인 팝업에서 [바꾸기]를 눌러야 바꾼다.
 *
 * @param props - 현재 입력 문구와 예시 선택 처리 함수
 * @returns 번호 라벨, 설명, 칩 목록과 확인 팝업
 */
export default function ExampleChips({ value, onSelect }: ExampleChipsProps) {
  const labelId = useId();
  // null이면 팝업 닫힘
  const [pending, setPending] = useState<PendingExample | null>(null);

  /** 칩을 누르면 문장을 고르고, 입력 상태에 따라 바로 채우거나 확인 팝업을 띄운다. */
  function handleClick(example: ExamplePrompt) {
    const prompt = pickPrompt(example, value);
    // 사용자가 직접 쓴 글이 아니면 지워져도 잃는 것이 없으므로 확인 없이 바꾼다
    if (value.trim() === "" || ALL_EXAMPLE_PROMPTS.has(value)) {
      onSelect(prompt);
      return;
    }
    setPending({ label: example.label, prompt });
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
      <SectionLabel
        id={labelId}
        number={2}
        title="예시 프롬프트"
        description="누를 때마다 다른 예시 문장이 채워져요"
      />

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
