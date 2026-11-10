/**
 * 에디터 AI 추천 탭의 추천안(칩)과 레이아웃·스타일 선택을 관리하는 훅.
 *
 * 생성일자: 2026-11-10
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  recommendLayout,
  type GenerateResponse,
  type ImageCopies,
  type LayoutCopy,
  type LayoutProposal,
} from "../api/client";
import { normalizeTextLayers, type TextLayer } from "../components/editor/textLayer";
import { COPY_ROLE_OPTIONS } from "../constants/copyRequests";
import { FALLBACK_STYLE_ID, pickRecommendedStyle } from "../constants/layoutOptions";
import type { AppliedProposal, TextLayers } from "./useTextLayers";

/** 이미지 한 장의 추천안 상태 */
export interface ProposalState {
  /** 지금 문구 상자를 만든 칩과 레이아웃·스타일 (되돌리기를 따라 바뀐다). 없으면 null */
  applied: AppliedProposal | null;
  /** 배치를 받아 오는 중인 칩 순서. 없으면 null */
  pendingChip: number | null;
  /** 배치 추천에 실패했을 때 보여줄 메시지 */
  error: string | null;
  /** 적용한 칩에 서버가 추천한 레이아웃 id. 아직 모르면 null */
  recommendedTemplateId: string | null;
  /** AI가 이 이미지에 추천한 스타일 id. 없으면 null */
  recommendedStyleId: string | null;
}

/** 레이아웃·스타일 중 바꿀 값 */
export interface LayoutChoice {
  templateId?: string;
  styleId?: string;
}

export interface CopyProposals {
  /** 이미지 순서(0부터)의 추천안 상태 */
  stateOf: (imageIndex: number) => ProposalState;
  /** 배치를 받아 오는 중이면 true (그동안 칩을 누를 수 없다) */
  busy: boolean;
  /**
   * 칩의 문구를 배치해 이미지의 문구 상자를 통째로 바꾼다 (되돌리기 가능).
   * 처음에는 추천 레이아웃·스타일을, 이미 골라 본 칩이면 마지막으로 고른 조합을 쓴다.
   */
  apply: (imageIndex: number, chipIndex: number) => Promise<boolean>;
  /** 적용한 칩의 레이아웃이나 스타일을 바꿔 다시 배치한다 */
  choose: (imageIndex: number, choice: LayoutChoice) => Promise<boolean>;
  /**
   * 추천안을 넣은 뒤 문구 상자를 고쳤는지 확인한다 (문구·위치·크기·색 등 무엇이든).
   * 되돌리기로 넣은 직후 상태로 돌아갔으면 고치지 않은 것으로 본다
   */
  isEdited: (imageIndex: number) => boolean;
}

/** 이미지 한 장의 요청 상태 */
interface RequestState {
  pendingChip: number | null;
  error: string | null;
  /** 칩 순서 → 서버가 추천한 레이아웃 id */
  recommendedTemplates: Record<number, string>;
}

const EMPTY_REQUEST: RequestState = { pendingChip: null, error: null, recommendedTemplates: {} };

const LAYOUT_FAILED_MESSAGE = "추천안을 적용하지 못했어요. 잠시 후 다시 시도해 주세요";

/**
 * 칩 하나에 들어갈 문구(같은 순서의 title, subtitle, text)를 모은다.
 *
 * @param copies - 이미지의 추천 문구
 * @param chipIndex - 칩 순서
 * @returns 역할별 문구 (빈 문구는 뺀다)
 */
export function chipCopies(copies: ImageCopies, chipIndex: number): LayoutCopy[] {
  return COPY_ROLE_OPTIONS.map(({ id }) => ({
    role: id,
    text: copies[id][chipIndex]?.text ?? "",
  })).filter((copy) => copy.text.trim() !== "");
}

/**
 * 이미지의 칩 수. 세 역할 목록 중 가장 짧은 길이다.
 *
 * @param copies - 이미지의 추천 문구
 * @returns 칩 수
 */
export function chipCount(copies: ImageCopies): number {
  return Math.min(...COPY_ROLE_OPTIONS.map(({ id }) => copies[id].length));
}

/**
 * 받아 둔 배치를 찾는 키를 만든다.
 *
 * @param imageIndex - 이미지 순서
 * @param chipIndex - 칩 순서
 * @param templateId - 레이아웃 id. 서버가 고르게 했으면 null
 * @param styleId - 스타일 id
 * @returns 키
 */
function cacheKey(
  imageIndex: number,
  chipIndex: number,
  templateId: string | null,
  styleId: string,
): string {
  return `${imageIndex}|${chipIndex}|${templateId ?? "auto"}|${styleId}`;
}

/**
 * 이미지마다 추천안 배치를 받아 적용한다. 적용 상태는 문구 상자의 되돌리기 기록에 함께 남고
 * (textLayers.appliedOf), 이 훅은 받아 둔 배치·요청 상태·추천 레이아웃을 기억한다.
 * 에디터를 나갔다 들어와도 유지되고, 생성 결과가 바뀌면 모두 비운다.
 *
 * @param result - 생성 결과 (바뀌면 상태를 비운다)
 * @param textLayers - 칩을 적용할 문구 상자
 * @returns 추천안 상태 조회, 칩 적용, 레이아웃·스타일 선택 함수
 */
export default function useCopyProposals(
  result: GenerateResponse | null,
  textLayers: TextLayers,
): CopyProposals {
  const [requestByImage, setRequestByImage] = useState<Record<number, RequestState>>({});
  const [busy, setBusy] = useState(false);
  // 받아 둔 배치 (cacheKey → 추천안)
  const cacheRef = useRef(new Map<string, LayoutProposal>());
  // 이미지 → 칩 → 마지막으로 고른 레이아웃·스타일. 칩을 다시 누르면 이 조합을 쓴다
  const choiceRef = useRef(new Map<number, Map<number, AppliedProposal>>());
  // 추천안으로 넣은 문구 상자 목록. 되돌리기 기록은 같은 목록을 그대로 돌려주므로,
  // 지금 목록이 여기 있으면 넣은 뒤 고치지 않은 상태다
  const insertedRef = useRef(new WeakSet<TextLayer[]>());
  // 생성 결과가 바뀐 뒤 늦게 도착한 응답은 버린다
  const resultRef = useRef(result);
  const busyRef = useRef(false);
  const { replace, appliedOf, layersOf } = textLayers;

  useEffect(() => {
    resultRef.current = result;
    cacheRef.current = new Map();
    choiceRef.current = new Map();
    insertedRef.current = new WeakSet();
    setRequestByImage({});
  }, [result]);

  const stateOf = useCallback(
    (imageIndex: number): ProposalState => {
      const request = requestByImage[imageIndex] ?? EMPTY_REQUEST;
      const applied = appliedOf(imageIndex);
      const copies = result?.images[imageIndex]?.copies;
      return {
        applied,
        pendingChip: request.pendingChip,
        error: request.error,
        recommendedTemplateId: applied
          ? (request.recommendedTemplates[applied.chipIndex] ?? null)
          : null,
        recommendedStyleId: copies ? pickRecommendedStyle(copies.styles) : null,
      };
    },
    [requestByImage, appliedOf, result],
  );

  const setRequest = useCallback(
    (imageIndex: number, next: (request: RequestState) => RequestState) => {
      setRequestByImage((prev) => ({
        ...prev,
        [imageIndex]: next(prev[imageIndex] ?? EMPTY_REQUEST),
      }));
    },
    [],
  );

  /**
   * 칩 문구를 주어진 레이아웃·스타일로 배치해 적용한다. 받아 둔 배치가 있으면 다시 묻지 않는다.
   *
   * @param imageIndex - 이미지 순서
   * @param chipIndex - 칩 순서
   * @param templateId - 레이아웃 id. null이면 서버가 고른다(추천 레이아웃)
   * @param styleId - 스타일 id
   * @returns 적용했으면 true
   */
  const request = useCallback(
    async (imageIndex: number, chipIndex: number, templateId: string | null, styleId: string) => {
      const image = result?.images[imageIndex];
      const copies = image?.copies;
      if (!image || !copies || busyRef.current) return false;

      const key = cacheKey(imageIndex, chipIndex, templateId, styleId);
      let proposal = cacheRef.current.get(key);
      if (!proposal) {
        busyRef.current = true;
        setBusy(true);
        setRequest(imageIndex, (prev) => ({ ...prev, pendingChip: chipIndex, error: null }));
        try {
          proposal = await recommendLayout({
            imageBase64: image.image_base64,
            copies: chipCopies(copies, chipIndex),
            accent: copies.accent,
            style: styleId,
            templateId: templateId ?? undefined,
          });
        } catch (error) {
          console.error("배치 추천 실패", error);
        } finally {
          busyRef.current = false;
          setBusy(false);
        }
        if (resultRef.current !== result) return false;
        if (proposal) {
          cacheRef.current.set(key, proposal);
          // 서버가 고른 레이아웃은 그 레이아웃을 직접 골랐을 때도 다시 쓴다
          cacheRef.current.set(
            cacheKey(imageIndex, chipIndex, proposal.template_id, styleId),
            proposal,
          );
        }
      }

      const layers = proposal ? normalizeTextLayers(proposal.layers) : [];
      if (!proposal || layers.length === 0) {
        setRequest(imageIndex, (prev) => ({
          ...prev,
          pendingChip: null,
          error: LAYOUT_FAILED_MESSAGE,
        }));
        return false;
      }

      const applied: AppliedProposal = {
        chipIndex,
        templateId: proposal.template_id,
        styleId: proposal.style,
      };
      insertedRef.current.add(layers);
      replace(imageIndex, layers, applied);
      const chips = choiceRef.current.get(imageIndex) ?? new Map<number, AppliedProposal>();
      chips.set(chipIndex, applied);
      choiceRef.current.set(imageIndex, chips);
      const recommendedTemplate = templateId === null ? proposal.template_id : null;
      setRequest(imageIndex, (prev) => ({
        pendingChip: null,
        error: null,
        recommendedTemplates: recommendedTemplate
          ? { ...prev.recommendedTemplates, [chipIndex]: recommendedTemplate }
          : prev.recommendedTemplates,
      }));
      return true;
    },
    [result, replace, setRequest],
  );

  const apply = useCallback(
    (imageIndex: number, chipIndex: number) => {
      const chosen = choiceRef.current.get(imageIndex)?.get(chipIndex);
      if (chosen) return request(imageIndex, chipIndex, chosen.templateId, chosen.styleId);
      const copies = result?.images[imageIndex]?.copies;
      const styleId = (copies && pickRecommendedStyle(copies.styles)) ?? FALLBACK_STYLE_ID;
      return request(imageIndex, chipIndex, null, styleId);
    },
    [result, request],
  );

  const choose = useCallback(
    async (imageIndex: number, choice: LayoutChoice) => {
      const applied = appliedOf(imageIndex);
      if (!applied) return false;
      const templateId = choice.templateId ?? applied.templateId;
      const styleId = choice.styleId ?? applied.styleId;
      // 이미 적용된 조합이면 되돌리기 기록을 늘리지 않는다
      if (templateId === applied.templateId && styleId === applied.styleId) return false;
      return request(imageIndex, applied.chipIndex, templateId, styleId);
    },
    [appliedOf, request],
  );

  const isEdited = useCallback(
    (imageIndex: number) =>
      appliedOf(imageIndex) !== null && !insertedRef.current.has(layersOf(imageIndex)),
    [appliedOf, layersOf],
  );

  return { stateOf, busy, apply, choose, isEdited };
}
