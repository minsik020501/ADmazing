/**
 * 입력 섹션 라벨 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import styles from "./SectionLabel.module.css";

export interface SectionLabelProps {
  /** 섹션 번호 (1. 프롬프트, 2. 예시 프롬프트 ...) */
  number: number;
  title: string;
  /** 제목 아래 회색 설명 */
  description?: string;
  /** 입력창의 라벨로 쓸 때 연결할 입력창 id. 있으면 <label>, 없으면 제목(<h3>)으로 그린다 */
  htmlFor?: string;
  /** 섹션을 aria-labelledby로 연결할 때 쓰는 id */
  id?: string;
}

/**
 * 시안의 "1. Prompt"처럼 번호가 붙은 섹션 제목과 설명.
 *
 * @param props - 번호, 제목, 설명, 연결할 입력창 id
 * @returns 섹션 라벨
 */
export default function SectionLabel({
  number,
  title,
  description,
  htmlFor,
  id,
}: SectionLabelProps) {
  const text = `${number}. ${title}`;

  return (
    <div>
      {htmlFor ? (
        <label id={id} htmlFor={htmlFor} className={styles.title}>
          {text}
        </label>
      ) : (
        <h3 id={id} className={styles.title}>
          {text}
        </h3>
      )}
      {description && <p className={styles.description}>{description}</p>}
    </div>
  );
}
