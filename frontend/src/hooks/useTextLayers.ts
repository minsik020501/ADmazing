/**
 * 이미지별 문구 상자 목록과 되돌리기 기록을 관리하는 훅.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

import { useCallback, useEffect, useState } from "react";
import { HISTORY_GROUP_MS, HISTORY_LIMIT, LAYER_LIMITS } from "../constants/editor";
import type { TextLayer } from "../components/editor/textLayer";

type LayerChanges = Partial<Omit<TextLayer, "id">>;

/**
 * 문구 상자 목록이 어떤 AI 추천안에서 왔는지. 되돌리기 기록에 함께 남아,
 * 되돌리면 AI 추천 탭의 칩·레이아웃·스타일 선택도 같이 돌아간다
 */
export interface AppliedProposal {
  /** 칩 순서 */
  chipIndex: number;
  /** 레이아웃 id */
  templateId: string;
  /** 글꼴 스타일 id */
  styleId: string;
}

export interface TextLayers {
  /** 이미지 순서(0부터)의 문구 상자 목록 */
  layersOf: (imageIndex: number) => TextLayer[];
  /** 문구 상자를 맨 위에 추가한다. 개수 제한을 넘으면 추가하지 않고 false */
  add: (imageIndex: number, layer: TextLayer) => boolean;
  /** 문구 상자의 일부 값을 바꾼다 */
  update: (imageIndex: number, id: string, changes: LayerChanges) => void;
  /** 문구 상자를 지운다 */
  remove: (imageIndex: number, id: string) => void;
  /** 문구를 다 지운 상자를 없앤다. 되돌리면 입력 전 문구가 있던 상자로 돌아간다 */
  removeEmpty: (imageIndex: number, id: string) => void;
  /**
   * 이미지의 문구 상자를 통째로 바꾼다 (리셋, AI 추천안 적용).
   * applied는 AI 추천안을 적용할 때 넘기고, 리셋처럼 추천안이 아니면 null이다
   */
  replace: (imageIndex: number, layers: TextLayer[], applied?: AppliedProposal | null) => void;
  /** 지금 문구 상자를 만든 AI 추천안. 추천안을 적용한 적이 없거나 리셋했으면 null */
  appliedOf: (imageIndex: number) => AppliedProposal | null;
  /** 한 단계 되돌린다 */
  undo: (imageIndex: number) => void;
  /** 되돌린 것을 한 단계 다시 실행한다 */
  redo: (imageIndex: number) => void;
  canUndo: (imageIndex: number) => boolean;
  canRedo: (imageIndex: number) => boolean;
  /** 이어지던 변경 묶음을 끝낸다. 다음 변경은 새 단계가 된다 (문구 입력이 끝났을 때 호출) */
  endChangeGroup: (imageIndex: number) => void;
}

/** 되돌리기 한 단계: 문구 상자 목록과 그 목록을 만든 AI 추천안 */
interface Snapshot {
  layers: TextLayer[];
  applied: AppliedProposal | null;
}

/** 이미지 한 장의 문구 상자와 되돌리기 기록 */
interface ImageHistory extends Snapshot {
  /** 지금보다 이전 상태들 (뒤에 있을수록 최근) */
  past: Snapshot[];
  /** 되돌려서 지나온 상태들 (앞에 있을수록 먼저 다시 실행) */
  future: Snapshot[];
  /** 마지막 변경의 묶음 이름. 같은 이름이 이어지면 한 단계로 합친다 */
  group: string | null;
  /** 마지막 변경 시각 (ms) */
  changedAt: number;
}

const EMPTY_HISTORY: ImageHistory = {
  layers: [],
  applied: null,
  past: [],
  future: [],
  group: null,
  changedAt: 0,
};

/**
 * 묶음 이름을 만든다. 같은 상자의 같은 항목을 바꾸는 변경끼리 이름이 같다.
 *
 * @param id - 문구 상자 id
 * @param changes - 바꿀 값
 * @returns 묶음 이름
 */
function toGroupName(id: string, changes: LayerChanges): string {
  return `${id}:${Object.keys(changes).sort().join(",")}`;
}

/**
 * 새 목록을 지금 상태로 만들고 이전 상태를 기록한다. 앞 변경과 묶이면 기록을 늘리지 않는다.
 *
 * @param history - 지금 기록
 * @param layers - 새 문구 상자 목록
 * @param now - 지금 시각 (ms)
 * @param group - 묶음 이름. null이면 항상 새 단계
 * @param groupMs - 앞 변경과 이 시간(ms) 안이면 묶는다
 * @param applied - 새 목록을 만든 AI 추천안. 생략하면 지금 값을 이어받는다(직접 편집)
 * @returns 새 기록
 */
function commit(
  history: ImageHistory,
  layers: TextLayer[],
  now: number,
  group: string | null = null,
  groupMs: number = HISTORY_GROUP_MS,
  applied: AppliedProposal | null = history.applied,
): ImageHistory {
  const merged = group !== null && group === history.group && now - history.changedAt < groupMs;
  const current: Snapshot = { layers: history.layers, applied: history.applied };
  return {
    layers,
    applied,
    past: merged ? history.past : [...history.past, current].slice(-HISTORY_LIMIT),
    future: [],
    group,
    changedAt: now,
  };
}

/**
 * 이미지마다 따로 문구 상자 목록과 되돌리기 기록을 기억한다. 에디터를 나갔다 들어와도 유지되고,
 * resetKey(생성 결과)가 바뀌면 모두 비운다.
 *
 * @param resetKey - 바뀌면 목록을 비울 값 (생성 결과)
 * @returns 문구 상자 목록 조회·변경·되돌리기 함수
 */
export default function useTextLayers(resetKey: unknown): TextLayers {
  // 이미지 순서 → 기록 (목록 순서가 그리는 순서, 뒤에 있을수록 위)
  const [historyByImage, setHistoryByImage] = useState<Record<number, ImageHistory>>({});

  useEffect(() => {
    setHistoryByImage({});
  }, [resetKey]);

  /** 이미지 한 장의 기록을 바꾼다. 바꿀 것이 없으면 원래 기록을 그대로 돌려준다. */
  const change = useCallback(
    (imageIndex: number, next: (history: ImageHistory) => ImageHistory) => {
      setHistoryByImage((prev) => {
        const history = prev[imageIndex] ?? EMPTY_HISTORY;
        const updated = next(history);
        return updated === history ? prev : { ...prev, [imageIndex]: updated };
      });
    },
    [],
  );

  const layersOf = useCallback(
    (imageIndex: number) => (historyByImage[imageIndex] ?? EMPTY_HISTORY).layers,
    [historyByImage],
  );

  const add = useCallback(
    (imageIndex: number, layer: TextLayer) => {
      const { layers } = historyByImage[imageIndex] ?? EMPTY_HISTORY;
      if (layers.length >= LAYER_LIMITS.layerCount.max) return false;
      const now = Date.now();
      change(imageIndex, (history) => commit(history, [...history.layers, layer], now));
      return true;
    },
    [historyByImage, change],
  );

  const update = useCallback(
    (imageIndex: number, id: string, changes: LayerChanges) => {
      const now = Date.now();
      // 문구 입력은 잠시 멈춰도 입력이 끝날 때까지 한 단계로 묶는다 (endChangeGroup)
      const groupMs = "text" in changes ? Infinity : HISTORY_GROUP_MS;
      change(imageIndex, (history) => {
        const target = history.layers.find((layer) => layer.id === id);
        const same =
          !target ||
          Object.entries(changes).every(([key, value]) => target[key as keyof TextLayer] === value);
        if (same) return history;
        const layers = history.layers.map((layer) =>
          layer.id === id ? { ...layer, ...changes } : layer,
        );
        return commit(history, layers, now, toGroupName(id, changes), groupMs);
      });
    },
    [change],
  );

  const remove = useCallback(
    (imageIndex: number, id: string) => {
      const now = Date.now();
      change(imageIndex, (history) =>
        commit(
          history,
          history.layers.filter((layer) => layer.id !== id),
          now,
        ),
      );
    },
    [change],
  );

  const removeEmpty = useCallback(
    (imageIndex: number, id: string) => {
      const now = Date.now();
      // 문구를 지운 입력과 같은 묶음으로 합쳐, 되돌릴 때 빈 상자가 나오지 않게 한다
      change(imageIndex, (history) =>
        commit(
          history,
          history.layers.filter((layer) => layer.id !== id),
          now,
          toGroupName(id, { text: "" }),
          Infinity,
        ),
      );
    },
    [change],
  );

  const replace = useCallback(
    (imageIndex: number, layers: TextLayer[], applied: AppliedProposal | null = null) => {
      const now = Date.now();
      change(imageIndex, (history) =>
        commit(history, layers, now, null, HISTORY_GROUP_MS, applied),
      );
    },
    [change],
  );

  const appliedOf = useCallback(
    (imageIndex: number) => (historyByImage[imageIndex] ?? EMPTY_HISTORY).applied,
    [historyByImage],
  );

  const undo = useCallback(
    (imageIndex: number) => {
      change(imageIndex, (history) => {
        const previous = history.past[history.past.length - 1];
        if (!previous) return history;
        return {
          ...previous,
          past: history.past.slice(0, -1),
          future: [{ layers: history.layers, applied: history.applied }, ...history.future],
          group: null,
          changedAt: 0,
        };
      });
    },
    [change],
  );

  const redo = useCallback(
    (imageIndex: number) => {
      change(imageIndex, (history) => {
        const [next, ...future] = history.future;
        if (!next) return history;
        return {
          ...next,
          past: [...history.past, { layers: history.layers, applied: history.applied }],
          future,
          group: null,
          changedAt: 0,
        };
      });
    },
    [change],
  );

  const canUndo = useCallback(
    (imageIndex: number) => (historyByImage[imageIndex] ?? EMPTY_HISTORY).past.length > 0,
    [historyByImage],
  );

  const canRedo = useCallback(
    (imageIndex: number) => (historyByImage[imageIndex] ?? EMPTY_HISTORY).future.length > 0,
    [historyByImage],
  );

  const endChangeGroup = useCallback(
    (imageIndex: number) => {
      change(imageIndex, (history) =>
        history.group === null ? history : { ...history, group: null },
      );
    },
    [change],
  );

  return {
    layersOf,
    add,
    update,
    remove,
    removeEmpty,
    replace,
    appliedOf,
    undo,
    redo,
    canUndo,
    canRedo,
    endChangeGroup,
  };
}
