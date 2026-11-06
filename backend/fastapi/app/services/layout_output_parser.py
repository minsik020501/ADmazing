"""문구 배치 추천 모델의 출력 문자열에서 추천안과 가리면 안 되는 영역(제품, 얼굴)을 꺼낸다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import json
import re

from app.services.layout_recommendation_error import LayoutRecommendationError

# 가장 큰 얼굴 넓이 대비 이보다 작은 얼굴은 배경 인물로 보고 뺀다
MIN_FACE_AREA_RATIO = 0.3

_CODE_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_proposals(output: str) -> list[dict]:
    """모델 출력에서 {"proposals": [...]}를 읽어 추천안 목록을 반환한다.

    코드 블록(```json)으로 감쌌거나 앞뒤에 설명이 붙어 있어도 첫 JSON 객체를 찾아 읽는다.
    각 추천안의 값 검사는 하지 않는다 (layout_guardrails에서 한다).

    Args:
        output: 모델이 생성한 문자열.

    Returns:
        list[dict]: 추천안 목록. 각 항목은 {"label", "layers"} 형태의 dict.

    Raises:
        LayoutRecommendationError: JSON을 찾을 수 없거나 형식이 틀렸을 때.
    """
    proposals = _load(output).get("proposals")
    if not isinstance(proposals, list):
        raise LayoutRecommendationError("모델 출력에 proposals 목록이 없습니다.")
    return [proposal for proposal in proposals if isinstance(proposal, dict)]


def parse_subjects(output: str) -> list[tuple[str, tuple[float, float, float, float]]]:
    """영역 찾기(SUBJECT_PROMPT) 출력에서 가리면 안 되는 영역 목록을 읽는다.

    Args:
        output: 모델이 생성한 문자열. [{"label", "bbox_2d": [x1, y1, x2, y2]}] (0~1000).

    Returns:
        list[tuple[str, tuple[float, float, float, float]]]: [(이름, (왼쪽, 위, 오른쪽,
            아래) 비율)]. 읽을 수 없으면 빈 목록.
    """
    fenced = _CODE_FENCE.search(output)
    text = fenced.group(1) if fenced else output
    start = text.find("[")
    if start < 0:
        return []
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return []
    subjects = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        box = _to_box(item.get("bbox_2d"))
        if box is not None:
            subjects.append((str(item.get("label") or "subject")[:20], box))
    return _drop_background_faces(subjects)


def _drop_background_faces(
    subjects: list[tuple[str, tuple[float, float, float, float]]],
) -> list[tuple[str, tuple[float, float, float, float]]]:
    """가장 큰 얼굴보다 훨씬 작은 얼굴(뒤쪽 행인 등)을 뺀다.

    작은 얼굴까지 합치면 가리면 안 되는 영역이 이미지 곳곳으로 넓어져 문구를 둘 곳이 없다.

    Returns:
        list[tuple[str, tuple[float, float, float, float]]]: 걸러 낸 영역 목록.
    """
    face_areas = [_area(box) for label, box in subjects if label == "face"]
    if not face_areas:
        return subjects
    limit = max(face_areas) * MIN_FACE_AREA_RATIO
    return [
        (label, box)
        for label, box in subjects
        if label != "face" or _area(box) >= limit
    ]


def _area(box: tuple[float, float, float, float]) -> float:
    """상자 넓이를 구한다.

    Returns:
        float: 넓이 (비율²).
    """
    return (box[2] - box[0]) * (box[3] - box[1])


def union_box(
    boxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float] | None:
    """상자들을 모두 감싸는 상자를 구한다.

    Returns:
        tuple[float, float, float, float] | None: 감싸는 상자. 상자가 없으면 None.
    """
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _to_box(value) -> tuple[float, float, float, float] | None:
    """[x1, y1, x2, y2] (0~1000)을 0~1 비율 상자로 바꾼다.

    Returns:
        tuple[float, float, float, float] | None: 상자. 형식이 틀렸거나 넓이가 0이면 None.
    """
    if not (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
    ):
        return None
    left, top, right, bottom = (min(max(v / 1000, 0.0), 1.0) for v in value)
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _load(output: str) -> dict:
    """모델 출력에서 첫 JSON 객체를 읽는다.

    Returns:
        dict: 읽은 JSON 객체.

    Raises:
        LayoutRecommendationError: JSON 객체를 찾을 수 없을 때.
    """
    fenced = _CODE_FENCE.search(output)
    text = fenced.group(1) if fenced else output
    start = text.find("{")
    if start < 0:
        raise LayoutRecommendationError("모델 출력에 JSON이 없습니다.")
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as error:
        raise LayoutRecommendationError(f"모델 출력 JSON 오류: {error}") from error
    if not isinstance(data, dict):
        raise LayoutRecommendationError("모델 출력이 JSON 객체가 아닙니다.")
    return data
