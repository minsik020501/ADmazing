/**
 * 에디터에서 쓸 글꼴 파일을 앱을 열 때 미리 받아 두는 훅.
 *
 * 생성일자: 2026-11-11
 * 생성자: bioyejin
 * 수정일자: 2026-11-11
 * 수정자: bioyejin
 */

import { useEffect } from "react";
import { DEFAULT_FONT_ID, FONT_PRELOAD_CONCURRENCY } from "../constants/editor";
import { AD_FONTS, toFontFamily, type AdFont } from "../constants/fonts";

// 미리 받을 때 쓰는 글자 크기 (크기와 상관없이 같은 파일을 받으므로 아무 값이나 됨)
const PRELOAD_SIZE_PX = 16;
// 브라우저가 한가해지기를 기다리는 최대 시간 (ms). 이 시간이 지나면 바로 시작한다
const IDLE_TIMEOUT_MS = 2000;

/**
 * 받을 순서를 정한다. 새 문구 상자의 기본 글꼴, 시그니처 글꼴을 먼저 받고 나머지는 목록 순서대로.
 *
 * @returns 글꼴 목록
 */
function preloadOrder(): AdFont[] {
  const rank = (font: AdFont) => {
    if (font.id === DEFAULT_FONT_ID) return 0;
    if (font.category === "signature") return 1;
    return 2;
  };
  // sort는 순위가 같으면 원래 순서를 지킨다
  return [...AD_FONTS].sort((a, b) => rank(a) - rank(b));
}

/**
 * 앱을 열고 첫 화면을 다 그린 뒤, 브라우저가 한가할 때 모든 글꼴 파일(굵기별)을 조금씩 받아 둔다.
 * 다 받아 두면 에디터에서 글꼴을 고르거나 글꼴 메뉴를 열 때 기다리지 않고 바로 보인다.
 * 아직 받지 못한 글꼴을 먼저 고르면 그 글꼴은 지금처럼 그때 받는다 (같은 파일은 한 번만 받는다).
 * 받은 파일은 브라우저에 저장되어 다음 접속부터는 다시 받지 않는다.
 */
export default function usePreloadFonts(): void {
  useEffect(() => {
    let cancelled = false;
    const queue = preloadOrder().flatMap((font) =>
      font.weights.map((weight) => `${weight} ${PRELOAD_SIZE_PX}px ${toFontFamily(font)}`),
    );

    // 한 줄씩 꺼내 받는다. FONT_PRELOAD_CONCURRENCY개가 동시에 돌며 큐를 나눠 맡는다
    async function worker() {
      while (!cancelled) {
        const font = queue.shift();
        if (!font) return;
        if (document.fonts.check(font)) continue;
        try {
          await document.fonts.load(font);
        } catch (error) {
          // 못 받아도 에디터에서 고를 때 다시 받으므로 기록만 남긴다
          console.warn("글꼴 미리 받기 실패", font, error);
        }
      }
    }

    function start() {
      for (let i = 0; i < FONT_PRELOAD_CONCURRENCY; i += 1) void worker();
    }

    // requestIdleCallback이 없는 브라우저(Safari 등)는 잠시 뒤에 시작한다
    if ("requestIdleCallback" in window) {
      const handle = window.requestIdleCallback(start, { timeout: IDLE_TIMEOUT_MS });
      return () => {
        cancelled = true;
        window.cancelIdleCallback(handle);
      };
    }
    const timer = setTimeout(start, IDLE_TIMEOUT_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);
}
