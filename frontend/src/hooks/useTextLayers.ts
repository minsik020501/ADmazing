/**
 * 이미지별 문구 상자 목록을 관리하는 훅.
 *
 * 생성일자: 2026-11-04
 * 생성자: bioyejin
 * 수정일자: 2026-11-04
 * 수정자: bioyejin
 */

import { useCallback, useEffect, useState } from "react";
import { LAYER_LIMITS } from "../constants/editor";
import type { TextLayer } from "../components/editor/textLayer";

export interface TextLayers {
  /** 이미지 순서(0부터)의 문구 상자 목록 */
  layersOf: (imageIndex: number) => TextLayer[];
  /** 문구 상자를 맨 위에 추가한다. 개수 제한을 넘으면 추가하지 않고 false */
  add: (imageIndex: number, layer: TextLayer) => boolean;
  /** 문구 상자의 일부 값을 바꾼다 */
  update: (imageIndex: number, id: string, changes: Partial<Omit<TextLayer, "id">>) => void;
  /** 문구 상자를 지운다 */
  remove: (imageIndex: number, id: string) => void;
  /** 이미지의 문구 상자를 통째로 바꾼다 (나중에 AI 추천안을 적용할 때 사용) */
  replace: (imageIndex: number, layers: TextLayer[]) => void;
}

/**
 * 이미지마다 따로 문구 상자 목록을 기억한다. 에디터를 나갔다 들어와도 유지되고,
 * resetKey(생성 결과)가 바뀌면 모두 비운다.
 *
 * @param resetKey - 바뀌면 목록을 비울 값 (생성 결과)
 * @returns 문구 상자 목록 조회·변경 함수
 */
export default function useTextLayers(resetKey: unknown): TextLayers {
  // 이미지 순서 → 문구 상자 목록 (목록 순서가 그리는 순서, 뒤에 있을수록 위)
  const [layersByImage, setLayersByImage] = useState<Record<number, TextLayer[]>>({});

  useEffect(() => {
    setLayersByImage({});
  }, [resetKey]);

  const layersOf = useCallback(
    (imageIndex: number) => layersByImage[imageIndex] ?? [],
    [layersByImage],
  );

  const add = useCallback(
    (imageIndex: number, layer: TextLayer) => {
      if ((layersByImage[imageIndex] ?? []).length >= LAYER_LIMITS.layerCount.max) return false;
      setLayersByImage((prev) => ({
        ...prev,
        [imageIndex]: [...(prev[imageIndex] ?? []), layer],
      }));
      return true;
    },
    [layersByImage],
  );

  const update = useCallback(
    (imageIndex: number, id: string, changes: Partial<Omit<TextLayer, "id">>) => {
      setLayersByImage((prev) => ({
        ...prev,
        [imageIndex]: (prev[imageIndex] ?? []).map((layer) =>
          layer.id === id ? { ...layer, ...changes } : layer,
        ),
      }));
    },
    [],
  );

  const remove = useCallback((imageIndex: number, id: string) => {
    setLayersByImage((prev) => ({
      ...prev,
      [imageIndex]: (prev[imageIndex] ?? []).filter((layer) => layer.id !== id),
    }));
  }, []);

  const replace = useCallback((imageIndex: number, layers: TextLayer[]) => {
    setLayersByImage((prev) => ({ ...prev, [imageIndex]: layers }));
  }, []);

  return { layersOf, add, update, remove, replace };
}
