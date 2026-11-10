/**
 * 문구 상자를 끌 때 캔버스 가운데선과 다른 문구 상자의 모서리·가운데에 맞추는 계산.
 * 화면과 상관없는 계산만 담는다 (단위는 모두 원본 이미지 px).
 *
 * 생성일자: 2026-11-10
 * 생성자: bioyejin
 * 수정일자: 2026-11-10
 * 수정자: bioyejin
 */

/** 상자의 가로·세로 테두리 (회전한 상자는 회전한 모양을 감싸는 테두리) */
export interface SnapBox {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

/** 안내선 하나 [x1, y1, x2, y2] */
export type SnapGuide = [number, number, number, number];

/** 맞춘 결과: 옮길 거리와 그릴 안내선 */
export interface SnapResult {
  dx: number;
  dy: number;
  guides: SnapGuide[];
}

/** 맞출 선 하나. box가 없으면 캔버스 가운데선 */
interface Target {
  value: number;
  box: SnapBox | null;
}

// 맞춘 뒤 같은 선 위에 있다고 볼 오차 (소수 계산 오차)
const ALIGNED_EPSILON = 0.5;

/**
 * 가운데 위치·크기·각도로 상자의 가로·세로 테두리를 구한다.
 *
 * @param centerX - 가운데 x
 * @param centerY - 가운데 y
 * @param width - 회전 전 폭
 * @param height - 회전 전 높이
 * @param rotation - 각도 (도)
 * @returns 테두리
 */
export function toSnapBox(
  centerX: number,
  centerY: number,
  width: number,
  height: number,
  rotation: number,
): SnapBox {
  const radians = (rotation * Math.PI) / 180;
  const cos = Math.abs(Math.cos(radians));
  const sin = Math.abs(Math.sin(radians));
  const halfWidth = (width * cos + height * sin) / 2;
  const halfHeight = (width * sin + height * cos) / 2;
  return {
    left: centerX - halfWidth,
    right: centerX + halfWidth,
    top: centerY - halfHeight,
    bottom: centerY + halfHeight,
  };
}

/**
 * 한 방향(가로 또는 세로)에서 가장 가까운 맞출 선까지의 거리를 찾는다.
 *
 * @param edges - 끄는 상자의 선 (시작·가운데·끝)
 * @param targets - 맞출 선
 * @param threshold - 이 거리 안이면 맞춘다
 * @returns 옮길 거리. 맞출 선이 없으면 0
 */
function nearestOffset(edges: number[], targets: Target[], threshold: number): number {
  let best = 0;
  let bestDistance = threshold;
  for (const edge of edges) {
    for (const target of targets) {
      const distance = Math.abs(target.value - edge);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = target.value - edge;
      }
    }
  }
  return best;
}

/**
 * 끄는 상자를 캔버스 가운데선과 다른 상자의 왼쪽·가운데·오른쪽(세로선),
 * 위·가운데·아래(가로선)에 맞춘다. 가로·세로는 따로 맞추고, 여러 선이 가까우면 가장 가까운 선에 맞춘다.
 * 안내선은 상자끼리는 두 상자에 걸친 길이만큼, 캔버스 가운데선은 캔버스 전체 길이로 그린다.
 *
 * @param moving - 끄는 상자 (맞추기 전 위치)
 * @param others - 다른 상자들
 * @param imageWidth - 캔버스 폭
 * @param imageHeight - 캔버스 높이
 * @param threshold - 이 거리 안이면 맞춘다
 * @returns 옮길 거리와 안내선
 */
export function snapToGuides(
  moving: SnapBox,
  others: SnapBox[],
  imageWidth: number,
  imageHeight: number,
  threshold: number,
): SnapResult {
  const xTargets: Target[] = [{ value: imageWidth / 2, box: null }];
  const yTargets: Target[] = [{ value: imageHeight / 2, box: null }];
  for (const box of others) {
    xTargets.push(
      { value: box.left, box },
      { value: (box.left + box.right) / 2, box },
      { value: box.right, box },
    );
    yTargets.push(
      { value: box.top, box },
      { value: (box.top + box.bottom) / 2, box },
      { value: box.bottom, box },
    );
  }

  const xEdges = [moving.left, (moving.left + moving.right) / 2, moving.right];
  const yEdges = [moving.top, (moving.top + moving.bottom) / 2, moving.bottom];
  const dx = nearestOffset(xEdges, xTargets, threshold);
  const dy = nearestOffset(yEdges, yTargets, threshold);
  const snapped: SnapBox = {
    left: moving.left + dx,
    right: moving.right + dx,
    top: moving.top + dy,
    bottom: moving.bottom + dy,
  };

  const guides: SnapGuide[] = [];
  const seen = new Set<string>();
  /** 같은 안내선을 두 번 그리지 않도록 모은다 */
  const push = (guide: SnapGuide) => {
    const key = guide.map((v) => Math.round(v)).join(",");
    if (!seen.has(key)) {
      seen.add(key);
      guides.push(guide);
    }
  };

  // 맞춘 뒤 끄는 상자의 선과 겹치는 선마다 안내선을 그린다
  for (const edge of xEdges.map((e) => e + dx)) {
    for (const target of xTargets) {
      if (Math.abs(target.value - edge) >= ALIGNED_EPSILON) continue;
      const top = target.box ? Math.min(target.box.top, snapped.top) : 0;
      const bottom = target.box ? Math.max(target.box.bottom, snapped.bottom) : imageHeight;
      push([target.value, top, target.value, bottom]);
    }
  }
  for (const edge of yEdges.map((e) => e + dy)) {
    for (const target of yTargets) {
      if (Math.abs(target.value - edge) >= ALIGNED_EPSILON) continue;
      const left = target.box ? Math.min(target.box.left, snapped.left) : 0;
      const right = target.box ? Math.max(target.box.right, snapped.right) : imageWidth;
      push([left, target.value, right, target.value]);
    }
  }
  return { dx, dy, guides };
}
