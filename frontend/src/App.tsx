/**
 * 메인 화면 컴포넌트.
 *
 * 생성일자: 2026-10-16
 * 생성자: ven_choi
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import { FormEvent, useState } from "react";
import { Menu } from "lucide-react";
import { generateImage, GenerateResponse } from "./api/client";
import Button from "./components/common/Button";
import ServerStatusBadge from "./components/layout/ServerStatusBadge";
import Sidebar from "./components/layout/Sidebar";
import ThemeToggle from "./components/layout/ThemeToggle";
import styles from "./App.module.css";

/**
 * 좌측 패널과 메인 영역(프롬프트 입력 폼, 생성 결과)으로 이루어진 화면.
 *
 * @returns 메인 화면
 */
export default function App() {
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  /** 입력값과 결과를 비우고 처음 상태로 돌아간다. */
  function handleNewProject() {
    setPrompt("");
    setResult(null);
    setError(null);
    setSidebarOpen(false);
  }

  /**
   * 입력한 프롬프트로 이미지 생성을 요청하고 결과를 상태에 반영한다.
   *
   * @param e - 폼 제출 이벤트
   */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setError(null);
    try {
      setResult(await generateImage(prompt));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewProject={handleNewProject}
      />

      <div className={styles.main}>
        <Button
          variant="ghost"
          size="sm"
          className={styles.menuButton}
          icon={<Menu size={16} />}
          aria-label="패널 열기"
          onClick={() => setSidebarOpen(true)}
        />

        {/* 기존 입력 폼과 결과 화면. 입력 화면 단계에서 새 컴포넌트로 교체 예정 */}
        <main className="container">
          <h1>👾 ADmazing</h1>
          <p>만들고 싶은 광고 이미지를 설명해 주세요.</p>

          <form onSubmit={handleSubmit}>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="예) 여름 해변에서 시원한 레몬 탄산음료를 들고 있는 모습, 밝고 청량한 분위기"
              rows={4}
            />
            <button type="submit" disabled={loading}>
              {loading ? "생성 중..." : "이미지 생성"}
            </button>
          </form>

          {error && <p className="error">{error}</p>}

          {result && (
            <section className="result">
              <p>
                <strong>번역된 프롬프트:</strong> {result.translated_prompt}
              </p>
              <div className="result-grid">
                {result.images.map((image, index) => (
                  <img
                    key={`${index}-${image.seed}`}
                    src={`data:image/png;base64,${image.image_base64}`}
                    alt={`${result.original_prompt} (${index + 1}/${result.images.length})`}
                  />
                ))}
              </div>
            </section>
          )}
        </main>
      </div>

      {/* 오른쪽 아래 상태 표시. 평소에는 흐리게, 마우스를 올리면 또렷하게 */}
      <div className={styles.statusBar}>
        <ServerStatusBadge />
        <ThemeToggle />
      </div>
    </>
  );
}
