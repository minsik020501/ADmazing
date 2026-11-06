"""문구 배치 추천 흐름(지시문 → 모델 생성 → JSON 읽기·재시도 → 가드레일) 서비스.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import logging
import time

from fastapi.concurrency import run_in_threadpool
from PIL import Image

from app.core.fonts import load_fonts
from app.schemas.layout_copy import LayoutCopy
from app.schemas.layout_proposal import LayoutProposal
from app.schemas.layout_recommend_request import LayoutRecommendRequest
from app.schemas.layout_recommend_response import LayoutRecommendResponse
from app.services.gpu_lock import gpu_lock
from app.services.layout_guardrails import build_proposals
from app.services.layout_output_parser import parse_proposals
from app.services.layout_prompt import build_user_prompt
from app.services.layout_recommendation_error import LayoutRecommendationError
from app.services.layout_recommender import LayoutRecommender
from app.utils.image import decode_base64_image

logger = logging.getLogger(__name__)

# greedy로 읽을 수 없는 출력이 나오면 같은 입력에 같은 출력이 나오므로 샘플링으로 한 번 더 한다
_ATTEMPTS = (False, True)


async def recommend_layouts(
    recommender: LayoutRecommender, req: LayoutRecommendRequest
) -> LayoutRecommendResponse:
    """이미지와 역할별 문구로 위치·글꼴·스타일 추천안을 만든다.

    모델 생성은 GPU 잠금을 잡고 스레드에서 실행하므로, 이미지 생성 중이면 끝날 때까지 기다린다.

    Args:
        recommender: 문구 배치 추천기.
        req: 이미지, 역할별 문구, 추천안 수를 담은 요청.

    Returns:
        LayoutRecommendResponse: 추천안 목록 (최대 req.num_proposals개).

    Raises:
        LayoutRecommendationError: 재시도 후에도 쓸 수 있는 추천안이 없을 때.
        GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
    """
    image = decode_base64_image(req.image_base64)
    proposals, _, _ = await run_in_threadpool(
        run_layout_recommendation, recommender, image, req.copies, req.num_proposals
    )
    return LayoutRecommendResponse(proposals=proposals)


def run_layout_recommendation(
    recommender: LayoutRecommender,
    image: Image.Image,
    copies: list[LayoutCopy],
    num_proposals: int,
) -> tuple[list[LayoutProposal], str, list[str]]:
    """모델로 추천안을 생성하고 가드레일을 거친다. Step 3 비교 스크립트도 이 함수를 쓴다.

    Args:
        recommender: 문구 배치 추천기.
        image: 원본 이미지.
        copies: 배치할 역할별 문구.
        num_proposals: 받을 추천안 수.

    Returns:
        tuple[list[LayoutProposal], str, list[str]]: 추천안, 마지막 모델 출력 원문,
            가드레일이 고친 내용 (재시도했다면 "retry: ..." 항목이 앞에 붙는다).

    Raises:
        LayoutRecommendationError: 재시도 후에도 쓸 수 있는 추천안이 없을 때.
        GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
    """
    user_prompt = build_user_prompt(
        copies, load_fonts(), image.width, image.height, num_proposals
    )
    notes: list[str] = []
    output = ""
    for sample in _ATTEMPTS:
        waited = time.perf_counter()
        with gpu_lock:
            started = time.perf_counter()
            output = recommender.generate(image, copies, user_prompt, sample=sample)
        logger.info(
            "문구 배치 추천: GPU 대기 %.1f초, 생성 %.1f초",
            started - waited,
            time.perf_counter() - started,
        )
        try:
            raw_proposals = parse_proposals(output)
        except LayoutRecommendationError as error:
            notes.append(f"retry: {error}")
            logger.warning("문구 배치 출력을 읽지 못했습니다: %s", error)
            continue
        proposals, fixes = build_proposals(raw_proposals, copies, image, num_proposals)
        if proposals:
            if fixes:
                logger.info("문구 배치 가드레일 보정 %d건: %s", len(fixes), fixes)
            return proposals, output, notes + fixes
        notes.append("retry: no usable proposals")
    raise LayoutRecommendationError(
        f"쓸 수 있는 추천안이 없습니다 ({'; '.join(notes)}). 마지막 출력: {output[:300]}"
    )
