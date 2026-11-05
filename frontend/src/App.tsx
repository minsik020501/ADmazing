/**
 * 메인 화면 컴포넌트.
 *
 * 생성일자: 2026-10-16
 * 생성자: ven_choi
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

import { useEffect, useRef, useState } from "react";
import { Menu } from "lucide-react";
import { fetchHealth } from "./api/client";
import Button from "./components/common/Button";
import EditorPage from "./components/editor/EditorPage";
import ExampleChips from "./components/input/ExampleChips";
import GenerateButton from "./components/input/GenerateButton";
import PromptInput from "./components/input/PromptInput";
import RatioPicker from "./components/input/RatioPicker";
import StylePicker from "./components/input/StylePicker";
import ServerStatusBadge, { type ServerStatus } from "./components/layout/ServerStatusBadge";
import Sidebar from "./components/layout/Sidebar";
import ThemeToggle from "./components/layout/ThemeToggle";
import LoadingOverlay from "./components/loading/LoadingOverlay";
import ResultSection from "./components/result/ResultSection";
import { DEFAULT_RATIO } from "./constants/imageRatios";
import { DEFAULT_STYLE_ID } from "./constants/stylePresets";
import useGeneration from "./hooks/useGeneration";
import useTextLayers from "./hooks/useTextLayers";
import styles from "./App.module.css";

/**
 * 좌측 패널과 메인 영역(프롬프트 입력 폼, 생성 결과)으로 이루어진 화면.
 *
 * @returns 메인 화면
 */
export default function App() {
  const [prompt, setPrompt] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [serverStatus, setServerStatus] = useState<ServerStatus>({ kind: "loading" });
  const [styleId, setStyleId] = useState(DEFAULT_STYLE_ID);
  const [ratio, setRatio] = useState(DEFAULT_RATIO);
  const generation = useGeneration();
  const { result, error, running: loading } = generation;
  // 에디터 화면을 보고 있으면 true. 결과로 돌아가도 편집 중이던 이미지 순서는 기억한다
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorIndex, setEditorIndex] = useState(0);
  // 이미지별 문구 상자. 에디터를 나갔다 와도 남고, 생성 결과가 바뀌면 비운다
  const textLayers = useTextLayers(result);

  // 스크롤되는 메인 영역 (생성이 끝나면 결과가 보이도록 맨 아래로 스크롤)
  const mainRef = useRef<HTMLDivElement>(null);

  const canGenerate = prompt.trim().length > 0 && !loading;

  // 생성이 끝나면 입력 아래에 붙은 결과 영역 전체가 보이도록 맨 아래까지 스크롤한다.
  // 이미지는 width·height 속성으로 자리를 미리 잡아 두어, 읽기 전에도 전체 높이가 정해져 있다.
  // 결과가 바뀌면(다시 생성, 새로 만들기) 에디터는 첫 번째 이미지부터 다시 시작한다
  useEffect(() => {
    setEditorIndex(0);
    const main = mainRef.current;
    if (result && main) main.scrollTo({ top: main.scrollHeight, behavior: "smooth" });
  }, [result]);

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

  /** 입력값, 생성 옵션, 결과를 비우고 처음 상태로 돌아간다. */
  function handleNewProject() {
    setPrompt("");
    setStyleId(DEFAULT_STYLE_ID);
    setRatio(DEFAULT_RATIO);
    generation.reset();
    setEditorOpen(false);
    setSidebarOpen(false);
  }

  /** 에디터 화면을 연다. 화면이 바뀌므로 맨 위부터 보여준다. */
  function handleOpenEditor() {
    setEditorOpen(true);
    mainRef.current?.scrollTo({ top: 0 });
  }

  /** 에디터에서 결과 영역으로 돌아간다. 결과가 바로 보이도록 맨 아래로 스크롤한다. */
  function handleCloseEditor() {
    setEditorOpen(false);
    // 입력·결과 화면이 다시 그려진 뒤에 스크롤해야 전체 높이를 알 수 있다
    requestAnimationFrame(() => {
      const main = mainRef.current;
      if (main) main.scrollTo({ top: main.scrollHeight });
    });
  }

  /** 입력한 프롬프트와 옵션으로 이미지 생성을 시작한다. 진행 상황은 로딩 화면에 표시된다. */
  function handleGenerate() {
    generation.start({ prompt, styleId, ratio });
  }

  // 입력·결과 화면과 에디터 화면 맨 위에 똑같이 보이는 타이틀
  const hero = (
    <header className={styles.hero}>
      <h1 className={styles.title}>👾 ADmazing</h1>
      <p className={styles.subtitle}>&gt; 새 광고 이미지 만들기</p>
    </header>
  );

  return (
    <>
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewProject={handleNewProject}
      />

      <div ref={mainRef} className={styles.main}>
        <Button
          variant="ghost"
          size="sm"
          className={styles.menuButton}
          icon={<Menu size={16} />}
          aria-label="패널 열기"
          onClick={() => setSidebarOpen(true)}
        />

        {editorOpen && result ? (
          <main className={styles.editorView}>
            {hero}
            <EditorPage
              result={result}
              index={editorIndex}
              onIndexChange={setEditorIndex}
              onBack={handleCloseEditor}
              textLayers={textLayers}
            />
          </main>
        ) : (
          <main className="container">
            {hero}

            <PromptInput
              value={prompt}
              onChange={setPrompt}
              onSubmit={handleGenerate}
              loading={loading}
            />
            <ExampleChips value={prompt} onSelect={setPrompt} />
            <StylePicker value={styleId} onChange={setStyleId} />
            <RatioPicker value={ratio} onChange={setRatio} />
            {generation.cancelled && <p className={styles.notice}>생성을 취소했어요</p>}
            <GenerateButton
              disabled={!canGenerate}
              loading={loading}
              onClick={handleGenerate}
              health={serverStatus.kind === "ok" ? serverStatus.health : null}
            />

            {error && <p className="error">{error}</p>}

            {result && generation.options && (
              <ResultSection
                result={result}
                options={generation.options}
                onRegenerate={generation.regenerate}
                onOpenEditor={handleOpenEditor}
              />
            )}
          </main>
        )}
      </div>

      {/* 오른쪽 아래 상태 표시. 평소에는 흐리게, 마우스를 올리면 또렷하게 */}
      <div className={styles.statusBar}>
        <ServerStatusBadge status={serverStatus} />
        <ThemeToggle />
      </div>

      {loading && <LoadingOverlay progress={generation.progress} onCancel={generation.cancel} />}
    </>
  );
}
