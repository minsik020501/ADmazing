/**
 * 메인 화면 컴포넌트.
 *
 * 생성일자: 2026-10-16
 * 생성자: ven_choi
 * 수정일자: 2026-10-22
 * 수정자: bioyejin
 */

import { useEffect, useState } from "react";
import { Menu } from "lucide-react";
import { fetchHealth, generateImage, GenerateResponse } from "./api/client";
import Button from "./components/common/Button";
import ExampleChips from "./components/input/ExampleChips";
import GenerateButton from "./components/input/GenerateButton";
import PromptInput from "./components/input/PromptInput";
import ServerStatusBadge, { type ServerStatus } from "./components/layout/ServerStatusBadge";
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
  const [serverStatus, setServerStatus] = useState<ServerStatus>({ kind: "loading" });

  const canGenerate = prompt.trim().length > 0 && !loading;

  // 화면을 열 때 서버 상태를 한 번 조회해 배지 등 여러 곳에서 함께 쓴다
  useEffect(() => {
    // 화면을 벗어난 뒤 늦게 도착한 응답은 무시한다
    let ignore = false;
    fetchHealth()
      .then((health) => {
        if (!ignore) setServerStatus({ kind: "ok", health });
      })
      .catch(() => {
        if (!ignore) setServerStatus({ kind: "error" });
      });
    return () => {
      ignore = true;
    };
  }, []);

  /** 입력값과 결과를 비우고 처음 상태로 돌아간다. */
  function handleNewProject() {
    setPrompt("");
    setResult(null);
    setError(null);
    setSidebarOpen(false);
  }

  /** 입력한 프롬프트로 이미지 생성을 요청하고 결과를 상태에 반영한다. */
  async function handleGenerate() {
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

        <main className="container">
          <header className={styles.hero}>
            <h1 className={styles.title}>👾 ADmazing</h1>
            <p className={styles.subtitle}>&gt; 새 광고 이미지 만들기</p>
          </header>

          <PromptInput
            value={prompt}
            onChange={setPrompt}
            onSubmit={handleGenerate}
            loading={loading}
          />
          <ExampleChips value={prompt} onSelect={setPrompt} />
          <GenerateButton
            disabled={!canGenerate}
            loading={loading}
            onClick={handleGenerate}
            health={serverStatus.kind === "ok" ? serverStatus.health : null}
          />

          {error && <p className="error">{error}</p>}

          {/* 임시 결과 표시. 결과 화면 단계에서 새 컴포넌트로 교체 예정 */}
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
        <ServerStatusBadge status={serverStatus} />
        <ThemeToggle />
      </div>
    </>
  );
}
