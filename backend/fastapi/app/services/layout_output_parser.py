"""문구 배치 추천 모델의 출력 문자열에서 추천안 JSON을 꺼낸다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import json
import re

from app.services.layout_recommendation_error import LayoutRecommendationError

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
    fenced = _CODE_FENCE.search(output)
    text = fenced.group(1) if fenced else output
    start = text.find("{")
    if start < 0:
        raise LayoutRecommendationError("모델 출력에 JSON이 없습니다.")
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as error:
        raise LayoutRecommendationError(f"모델 출력 JSON 오류: {error}") from error

    proposals = data.get("proposals") if isinstance(data, dict) else None
    if not isinstance(proposals, list):
        raise LayoutRecommendationError("모델 출력에 proposals 목록이 없습니다.")
    return [proposal for proposal in proposals if isinstance(proposal, dict)]
