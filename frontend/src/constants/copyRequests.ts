/**
 * 입력 화면의 삽입할 문구 설정. AI가 문구를 추천할 때 참고할 역할별 요청 내용이다.
 *
 * 생성일자: 2026-11-06
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

/** 문구 역할 */
export type CopyRole = "title" | "subtitle" | "text";

/** 입력 줄 하나 */
export interface CopyRequestRow {
  /** 화면에서 줄을 구분하는 id */
  id: number;
  role: CopyRole;
  text: string;
}

/** 역할 하나의 화면 설정 */
export interface CopyRoleOption {
  id: CopyRole;
  label: string;
  /** 입력할 수 있는 최대 글자 수 */
  maxLength: number;
  /** 입력 칸의 회색 예시 문구 */
  placeholder: string;
}

/**
 * 역할 목록 (화면에 보여 줄 순서). 첫 번째 역할이 새 줄의 기본값이다.
 * 같은 역할을 여러 줄에서 고를 수는 있지만, 그 상태로는 생성할 수 없다
 */
export const COPY_ROLE_OPTIONS: CopyRoleOption[] = [
  {
    id: "title",
    label: "Title",
    maxLength: 20,
    placeholder: "할인 행사/신메뉴 출시/이벤트 등을 짧게 강조해주세요. (20자 이내)",
  },
  {
    id: "subtitle",
    label: "Subtitle",
    maxLength: 30,
    placeholder: "장점이나 특징을 강조해주세요. (30자 이내)",
  },
  {
    id: "text",
    label: "Text",
    maxLength: 100,
    placeholder: "꼭 들어가야 할 정보(가격, 날짜 등)를 기재해주세요. (100자 이내)",
  },
];

/** 입력 줄 최대 개수 */
export const MAX_COPY_REQUEST_ROWS = 3;

/** 입력 줄의 문제. 문제가 하나라도 있으면 생성할 수 없다 */
export interface CopyRequestProblems {
  /** 내용이 있는 줄 두 개 이상에서 고른 역할 */
  duplicateRoles: Set<CopyRole>;
  /** 글자 수 제한을 넘은 줄의 역할 (COPY_ROLE_OPTIONS 순서, 중복 없음) */
  overLimitRoles: CopyRole[];
}

/**
 * 역할의 화면 설정을 찾는다.
 *
 * @param role - 역할
 * @returns 역할 설정 (COPY_ROLE_OPTIONS의 항목)
 */
export function getCopyRoleOption(role: CopyRole): CopyRoleOption {
  return COPY_ROLE_OPTIONS.find((option) => option.id === role) ?? COPY_ROLE_OPTIONS[0];
}

/**
 * 입력 줄의 문제(역할 중복, 글자 수 초과)를 찾는다.
 * 역할 중복은 내용이 있는 줄만 센다. 빈 줄은 서버로 보내지 않기 때문이다.
 *
 * @param rows - 입력 줄 목록
 * @returns 겹친 역할과 글자 수를 넘은 역할
 */
export function findCopyRequestProblems(rows: CopyRequestRow[]): CopyRequestProblems {
  const seen = new Set<CopyRole>();
  const duplicateRoles = new Set<CopyRole>();
  for (const row of rows) {
    if (row.text.trim() === "") continue;
    if (seen.has(row.role)) duplicateRoles.add(row.role);
    seen.add(row.role);
  }
  const overLimitRoles = COPY_ROLE_OPTIONS.filter((option) =>
    rows.some((row) => row.role === option.id && row.text.length > option.maxLength),
  ).map((option) => option.id);
  return { duplicateRoles, overLimitRoles };
}

/**
 * 입력 줄에 생성을 막는 문제가 있는지 확인한다.
 *
 * @param rows - 입력 줄 목록
 * @returns 역할이 겹치거나 글자 수를 넘은 줄이 있으면 true
 */
export function hasCopyRequestProblems(rows: CopyRequestRow[]): boolean {
  const { duplicateRoles, overLimitRoles } = findCopyRequestProblems(rows);
  return duplicateRoles.size > 0 || overLimitRoles.length > 0;
}

/**
 * 같은 역할을 두 줄 이상에 입력했을 때의 안내 문구.
 *
 * @param role - 겹친 역할
 * @returns 예: "Title 문구는 1개만 입력할 수 있어요"
 */
export function duplicateRoleMessage(role: CopyRole): string {
  return `${getCopyRoleOption(role).label} 문구는 1개만 입력할 수 있어요`;
}

/**
 * 글자 수 제한을 넘은 역할을 한 줄로 알려 주는 안내 문구.
 *
 * @param roles - 글자 수를 넘은 역할 (1개 이상)
 * @returns 예: "Title, Subtitle 글자 수를 줄여 주세요"
 */
export function overLimitMessage(roles: CopyRole[]): string {
  const labels = roles.map((role) => getCopyRoleOption(role).label).join(", ");
  return `${labels} 글자 수를 줄여 주세요`;
}

let nextRowId = 0;

/**
 * 빈 입력 줄을 만든다.
 *
 * @param role - 줄의 역할
 * @returns 새 입력 줄
 */
export function createCopyRequestRow(role: CopyRole): CopyRequestRow {
  nextRowId += 1;
  return { id: nextRowId, role, text: "" };
}
