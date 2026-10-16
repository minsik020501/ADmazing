/**
 * Vite 설정. /api 요청을 백엔드로 프록시한다.
 *
 * 생성일자: 2026-10-16
 * 생성자: ven_choi
 * 수정일자: 2026-10-16
 * 수정자: ven_choi
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 12000,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:11000",
        changeOrigin: true,
      },
    },
  },
});
