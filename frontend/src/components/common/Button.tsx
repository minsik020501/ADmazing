/**
 * 공통 버튼 컴포넌트.
 *
 * 생성일자: 2026-10-20
 * 생성자: bioyejin
 * 수정일자: 2026-10-20
 * 수정자: bioyejin
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import styles from "./Button.module.css";

/** 버튼 종류: primary(주요 동작), secondary(보조 동작), ghost(배경 없는 가벼운 동작) */
export type ButtonVariant = "primary" | "secondary" | "ghost";

/** 버튼 크기 */
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** 글자 앞에 붙는 아이콘. 글자 없이 아이콘만 쓸 때는 aria-label을 함께 지정 */
  icon?: ReactNode;
}

/**
 * 화면 전체에서 모양이 통일된 버튼.
 * ref를 넘기면 내부 button 요소에 연결된다(팝업이 열릴 때 포커스 이동 등에 사용).
 *
 * @param props - 버튼 종류, 크기, 아이콘과 기본 button 속성
 * @param ref - 내부 button 요소 참조
 * @returns 버튼 요소
 */
const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", icon, type = "button", className, children, ...rest },
  ref,
) {
  const classes = [styles.button, styles[variant], styles[size], className]
    .filter(Boolean)
    .join(" ");

  return (
    <button ref={ref} type={type} className={classes} {...rest}>
      {icon && <span className={styles.icon}>{icon}</span>}
      {children}
    </button>
  );
});

export default Button;
