/**
 * React 앱 진입점.
 *
 * 생성일자: 2026-10-16
 * 생성자: ven_choi
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
// 광고 문구용 웹폰트. 실제로 쓰일 때만 내려받는다
import "./styles/fonts.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
