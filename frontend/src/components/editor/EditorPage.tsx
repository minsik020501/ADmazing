/**
 * 텍스트 에디터 화면 컴포넌트.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

import { ArrowLeft, Download } from "lucide-react";
import type { GenerateResponse } from "../../api/client";
import Button from "../common/Button";
import { base64ToBlob, downloadBlob, toImageFileName } from "./download";
import ThumbnailStrip from "./ThumbnailStrip";
import styles from "./EditorPage.module.css";

export interface EditorPageProps {
  result: GenerateResponse;
  /** 편집 중인 이미지 순서(0부터) */
  index: number;
  /** 썸네일을 눌러 다른 이미지를 고를 때 호출 */
  onIndexChange: (index: number) => void;
  /** [← 이전 화면으로]를 누를 때 호출 */
  onBack: () => void;
}

/**
 * 위에 썸네일 줄, 가운데 큰 이미지와 오른쪽 문구 패널, 아래 가운데 저장 버튼이 있는 편집 화면.
 * 지금은 이미지를 고르고 원본을 저장할 수 있다. 문구 넣기와 편집본 저장은 다음 단계에서 추가한다.
 *
 * @param props - 생성 결과, 편집 중인 이미지 순서, 이미지 고르기·돌아가기 처리 함수
 * @returns 에디터 화면
 */
export default function EditorPage({ result, index, onIndexChange, onBack }: EditorPageProps) {
  const count = result.images.length;
  const image = result.images[index];
  if (!image) return null;

  /** 지금 보고 있는 이미지를 서버가 보낸 원본 그대로 PNG로 내려받는다. */
  function handleSaveOriginal() {
    downloadBlob(base64ToBlob(image.image_base64), toImageFileName(image.seed));
  }

  return (
    <div className={styles.page}>
      <div className={styles.toolbar}>
        <Button
          variant="ghost"
          className={styles.backButton}
          icon={<ArrowLeft size={18} />}
          onClick={onBack}
        >
          이전 화면으로
        </Button>
      </div>

      <ThumbnailStrip
        images={result.images}
        selectedIndex={index}
        width={result.width}
        height={result.height}
        onSelect={onIndexChange}
      />

      <div className={styles.workspace}>
        <div className={styles.stage}>
          <img
            className={styles.image}
            src={`data:image/png;base64,${image.image_base64}`}
            alt={`${result.original_prompt} (${index + 1}/${count})`}
            width={result.width}
            height={result.height}
          />
        </div>

        {/* 나중에 위쪽에 'AI 추천안', 아래쪽에 문구 속성이 들어가는 자리 */}
        <aside className={styles.panel} aria-label="문구 편집">
          <section className={styles.panelSection}>
            <h2 className={styles.panelTitle}>문구</h2>
            <p className={styles.panelHint}>텍스트 상자 추가와 편집 기능은 준비 중이에요</p>
          </section>
        </aside>
      </div>

      <div className={styles.saveArea}>
        <div className={styles.actions}>
          <Button icon={<Download size={14} />} onClick={handleSaveOriginal}>
            원본 저장
          </Button>
          <Button
            variant="primary"
            icon={<Download size={14} />}
            disabled
            title="문구 넣기 기능이 추가되면 사용할 수 있어요"
          >
            편집본 저장
          </Button>
        </div>
        <p className={styles.hint}>PNG 형식으로 한 장씩 저장돼요</p>
      </div>
    </div>
  );
}
