/**
 * 삽입할 문구 입력 컴포넌트.
 *
 * 생성일자: 2026-11-06
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { useId, type KeyboardEvent } from "react";
import { ChevronDown, Plus, X } from "lucide-react";
import {
  COPY_ROLE_OPTIONS,
  MAX_COPY_REQUEST_ROWS,
  createCopyRequestRow,
  duplicateRoleMessage,
  findCopyRequestProblems,
  getCopyRoleOption,
  overLimitMessage,
  type CopyRequestRow,
  type CopyRole,
} from "../../constants/copyRequests";
import Button from "../common/Button";
import SectionLabel from "../common/SectionLabel";
import styles from "./CopyRequestInput.module.css";

export interface CopyRequestInputProps {
  /** 입력 줄 목록. 값은 App이 보관한다(새로 만들기 시 초기화 등) */
  rows: CopyRequestRow[];
  onChange: (rows: CopyRequestRow[]) => void;
}

/**
 * 문구 요청은 한 줄짜리 내용이므로 Enter로 줄을 나누지 않는다. 긴 내용은 칸 안에서 자동으로
 * 줄바꿈된다. 한글 조합 중의 Enter는 글자 확정에 쓰이므로 막지 않는다.
 *
 * @param e - 입력 칸의 키 이벤트
 */
function preventLineBreak(e: KeyboardEvent<HTMLTextAreaElement>) {
  if (e.key === "Enter" && !e.nativeEvent.isComposing) e.preventDefault();
}

/**
 * "3. 삽입할 문구 (선택)" 섹션. 역할을 고르고 원하는 내용을 적으면 AI가 참고해 문구를 추천한다.
 * 처음에는 한 줄만 보이고 [추가]로 최대 3줄까지 늘릴 수 있다.
 * 같은 역할을 여러 줄에서 고르거나 글자 수를 넘기면 안내를 보여주고, App이 생성을 막는다.
 *
 * @param props - 입력 줄 목록과 변경 처리 함수
 * @returns 삽입할 문구 섹션
 */
export default function CopyRequestInput({ rows, onChange }: CopyRequestInputProps) {
  const labelId = useId();
  const { duplicateRoles, overLimitRoles } = findCopyRequestProblems(rows);
  const canRemove = rows.length > 1;

  /** 줄의 역할을 바꾼다. 내용은 그대로 두고, 넘친 글자 수는 빨간색으로 보여준다. */
  function handleRoleChange(id: number, role: CopyRole) {
    onChange(rows.map((row) => (row.id === id ? { ...row, role } : row)));
  }

  /** 줄의 내용을 바꾼다. 붙여 넣은 줄바꿈은 공백으로 바꾼다. */
  function handleTextChange(id: number, value: string) {
    const text = value.replace(/[\r\n]+/g, " ");
    onChange(rows.map((row) => (row.id === id ? { ...row, text } : row)));
  }

  /** 첫 번째 역할(Title)로 새 줄을 추가한다. */
  function handleAdd() {
    onChange([...rows, createCopyRequestRow(COPY_ROLE_OPTIONS[0].id)]);
  }

  return (
    <section className={styles.section} aria-labelledby={labelId}>
      <SectionLabel
        id={labelId}
        number={3}
        title="삽입할 문구 (선택)"
        description="입력하지 않으면 전부 AI 추천안으로 생성해요"
      />

      <div className={styles.rows}>
        {rows.map((row, index) => {
          const option = getCopyRoleOption(row.role);
          // 빈 줄은 역할이 겹쳐도 표시하지 않는다
          const duplicate = duplicateRoles.has(row.role) && row.text.trim() !== "";
          const over = row.text.length > option.maxLength;
          return (
            <div key={row.id} className={styles.row}>
              <div className={styles.roleBox}>
                <select
                  className={`${styles.role} ${duplicate ? styles.invalid : ""}`}
                  aria-label={`${index + 1}번째 문구 역할`}
                  aria-invalid={duplicate}
                  value={row.role}
                  onChange={(e) => handleRoleChange(row.id, e.target.value as CopyRole)}
                >
                  {COPY_ROLE_OPTIONS.map((roleOption) => (
                    <option key={roleOption.id} value={roleOption.id}>
                      {roleOption.label}
                    </option>
                  ))}
                </select>
                <ChevronDown size={16} className={styles.arrow} aria-hidden />
              </div>

              {/* 숨은 복사본이 내용만큼 높이를 잡아 입력 칸이 스크롤 없이 세로로 늘어난다.
                  예시 문구는 높이에 넣지 않아 빈 칸은 항상 한 줄 높이다 */}
              <div className={styles.field} data-value={row.text}>
                <textarea
                  rows={1}
                  className={`${styles.input} ${over ? styles.invalid : ""}`}
                  aria-label={`${index + 1}번째 문구 내용`}
                  aria-invalid={over}
                  value={row.text}
                  placeholder={option.placeholder}
                  onChange={(e) => handleTextChange(row.id, e.target.value)}
                  onKeyDown={preventLineBreak}
                />
                <span className={styles.count}>
                  <span className={over ? styles.countOver : undefined}>{row.text.length}</span>/
                  {option.maxLength}
                </span>
              </div>

              {/* 줄이 하나일 때도 자리를 남겨 입력 칸 길이를 똑같이 유지한다 */}
              <Button
                variant="ghost"
                size="sm"
                className={`${styles.remove} ${canRemove ? "" : styles.hidden}`}
                icon={<X size={16} />}
                aria-label={`${index + 1}번째 문구 지우기`}
                disabled={!canRemove}
                onClick={() => onChange(rows.filter((other) => other.id !== row.id))}
              />
            </div>
          );
        })}
      </div>

      {(duplicateRoles.size > 0 || overLimitRoles.length > 0) && (
        <div className={styles.notices} role="alert">
          {[...duplicateRoles].map((role) => (
            <p key={role} className={styles.notice}>
              {duplicateRoleMessage(role)}
            </p>
          ))}
          {overLimitRoles.length > 0 && (
            <p className={styles.notice}>{overLimitMessage(overLimitRoles)}</p>
          )}
        </div>
      )}

      <div className={styles.addRow}>
        <Button
          size="sm"
          className={styles.add}
          icon={<Plus size={16} />}
          disabled={rows.length >= MAX_COPY_REQUEST_ROWS}
          onClick={handleAdd}
        >
          추가
        </Button>
      </div>
    </section>
  );
}
