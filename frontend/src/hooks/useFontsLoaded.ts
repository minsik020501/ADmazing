/**
 * 캔버스에 그릴 웹폰트를 미리 받는 훅.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

import { useEffect, useState } from "react";

/**
 * 캔버스는 글꼴 파일이 오기 전에 그리면 기본 글꼴로 그리고 다시 그리지 않는다.
 * 그래서 쓰는 글꼴을 미리 받고, 다 받으면 바뀌는 숫자를 돌려줘 다시 그리게 한다.
 *
 * @param fonts - CSS font 값 목록 (예: `700 32px "Pretendard", sans-serif`)
 * @returns 글꼴을 새로 받을 때마다 1씩 커지는 숫자
 */
export default function useFontsLoaded(fonts: string[]): number {
  const [version, setVersion] = useState(0);
  // 배열은 렌더마다 새로 만들어지므로 내용으로 비교한다
  const key = [...new Set(fonts)].sort().join("\n");

  useEffect(() => {
    const pending = key.split("\n").filter((font) => font && !document.fonts.check(font));
    if (pending.length === 0) return;

    let ignore = false;
    Promise.allSettled(pending.map((font) => document.fonts.load(font))).then(() => {
      if (!ignore) setVersion((value) => value + 1);
    });
    return () => {
      ignore = true;
    };
  }, [key]);

  return version;
}
