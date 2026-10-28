/**
 * 라이트/다크 테마 전환 버튼 컴포넌트.
 *
 * 생성일자: 2026-10-22
 * 생성자: bioyejin
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import { useState } from "react";
import { Moon, Sun } from "lucide-react";
import Button from "../common/Button";

type Theme = "light" | "dark";

/** 선택한 테마를 저장하는 키. index.html의 테마 적용 스크립트와 같은 값이어야 한다 */
const STORAGE_KEY = "admazing-theme";

/**
 * 지금 화면에 적용된 테마를 구한다. 직접 고른 적이 없으면 기기 설정을 따른다.
 *
 * @returns 현재 테마
 */
function getCurrentTheme(): Theme {
  const selected = document.documentElement.dataset.theme;
  if (selected === "light" || selected === "dark") return selected;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * 누를 때마다 라이트 ↔ 다크로 바꾸는 버튼.
 * <html data-theme>을 바꿔 tokens.css의 테마 색을 적용하고, 선택을 브라우저에 저장한다.
 *
 * @returns 테마 전환 버튼
 */
export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(getCurrentTheme);

  /** 반대 테마를 적용하고 저장한다. */
  function handleToggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // 저장소를 쓸 수 없는 환경(시크릿 창 등)에서도 지금 화면에는 적용된다
    }
    setTheme(next);
  }

  const label = theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환";

  return (
    <Button
      variant="ghost"
      size="sm"
      icon={theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      aria-label={label}
      title={label}
      onClick={handleToggle}
    />
  );
}
