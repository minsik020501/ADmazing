/**
 * 생성 결과 영역 컴포넌트.
 *
 * 생성일자: 2026-11-02
 * 생성자: bioyejin
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

import { useState } from "react";
import { RotateCw, Type } from "lucide-react";
import type { GenerateOptions, GenerateResponse } from "../../api/client";
import { IMAGE_RATIOS } from "../../constants/imageRatios";
import { DEFAULT_STYLE_ID, STYLE_PRESETS } from "../../constants/stylePresets";
import Button from "../common/Button";
import Modal from "../common/Modal";
import ImageViewer from "./ImageViewer";
import styles from "./ResultSection.module.css";

/**
 * 생성할 때 쓴 옵션을 한 줄 요약으로 만든다. 예: "실사 사진 · 4:5 세로 피드 · 2장"
 *
 * @param options - 생성할 때 쓴 옵션
 * @param count - 생성된 이미지 장수
 * @returns 옵션 요약 문구
 */
function toSummary(options: GenerateOptions, count: number): string {
  const style =
    options.styleId === DEFAULT_STYLE_ID
      ? "스타일 없음"
      : (STYLE_PRESETS.find((preset) => preset.id === options.styleId)?.label ?? options.styleId);
  const ratio = IMAGE_RATIOS.find((item) => item.value === options.ratio);
  const ratioText = ratio ? `${ratio.value} ${ratio.label}` : options.ratio;
  return `${style} · ${ratioText} · ${count}장`;
}

export interface ResultSectionProps {
  result: GenerateResponse;
  /** 이 결과를 생성할 때 쓴 옵션 */
  options: GenerateOptions;
  /** 팝업에서 다시 생성을 확인했을 때 호출 */
  onRegenerate: () => void;
  /** [텍스트 삽입하기]를 누를 때 호출 */
  onOpenEditor: () => void;
}

/**
 * 번역된 프롬프트, 옵션 요약, 같은 크기의 이미지 격자, [다시 생성하기]·[텍스트 삽입하기] 버튼을 보여준다.
 * 이미지를 누르면 크게 보기 레이어가, [다시 생성하기]를 누르면 확인 팝업이 뜬다.
 *
 * @param props - 생성 결과, 생성할 때 쓴 옵션, 다시 생성·에디터 열기 처리 함수
 * @returns 생성 결과 영역
 */
export default function ResultSection({
  result,
  options,
  onRegenerate,
  onOpenEditor,
}: ResultSectionProps) {
  // 크게 보고 있는 이미지 순서. null이면 닫힘
  const [viewIndex, setViewIndex] = useState<number | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const count = result.images.length;

  return (
    <section className={styles.section} aria-label="생성 결과">
      <p className={styles.prompt}>
        <strong>번역된 프롬프트:</strong> {result.translated_prompt}
      </p>
      <p className={styles.summary}>{toSummary(options, count)}</p>

      <div className={styles.grid}>
        {result.images.map((image, index) => (
          <button
            key={`${index}-${image.seed}`}
            type="button"
            className={styles.imageButton}
            aria-label={`${index + 1}번째 이미지 크게 보기`}
            onClick={() => setViewIndex(index)}
          >
            <img
              className={styles.image}
              src={`data:image/png;base64,${image.image_base64}`}
              alt={`${result.original_prompt} (${index + 1}/${count})`}
              width={result.width}
              height={result.height}
            />
          </button>
        ))}
      </div>

      <div className={styles.actions}>
        <Button icon={<RotateCw size={14} />} onClick={() => setConfirmOpen(true)}>
          다시 생성하기
        </Button>
        <Button variant="primary" icon={<Type size={14} />} onClick={onOpenEditor}>
          텍스트 삽입하기
        </Button>
      </div>

      <ImageViewer
        images={result.images}
        index={viewIndex}
        alt={result.original_prompt}
        onIndexChange={setViewIndex}
        onClose={() => setViewIndex(null)}
      />
      <Modal
        open={confirmOpen}
        title="같은 옵션으로 다시 생성할까요?"
        confirmLabel="다시 생성"
        onConfirm={() => {
          setConfirmOpen(false);
          onRegenerate();
        }}
        onCancel={() => setConfirmOpen(false)}
      />
    </section>
  );
}
