"""이미지별 광고 문구 추천 흐름(요청 개수 계산 → 추천 → 정리·재요청 → 조립) 서비스.

이미지 생성 작업(/api/jobs, /api/generate)과 단독 문구 추천(/api/copy/recommend)이
같은 흐름을 쓴다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import asyncio
import contextlib
import logging
import re

from app.core.config import settings
from fastapi.concurrency import run_in_threadpool

from app.core.copy_role import (
    COPIES_PER_ROLE,
    COPY_ROLES,
    CopyRole,
    copy_max_length,
)
from app.core.layout_templates import FontStyle
from app.schemas.copy_suggestion import CopySuggestion
from app.schemas.image_copies import ImageCopies
from app.services.copy_recommendation_error import (
    COPY_RECOMMENDATION_FAILED_MESSAGE,
    CopyRecommendationError,
)
from app.services.copy_recommender import CopyRecommender
from app.services.generation_cancelled_error import GenerationCancelledError
from app.services.generation_job import GenerationJob
from app.utils.image import decode_base64_image
from app.utils.image_palette import extract_palette

logger = logging.getLogger(__name__)

# 길이 초과·중복으로 버려질 묶음을 감안해 필요한 개수보다 더 받는다
_EXTRA_CANDIDATES = 2
# 정리 후에도 모자랄 때 모자란 만큼 다시 요청하는 횟수
_MAX_RETRIES = 1
# 문구 앞뒤에서 지우는 따옴표·괄호
_QUOTE_CHARS = "\"'“”‘’「」『』《》〈〉`"
# 중복 비교에서 무시하는 문자 (공백, 문장 부호)
_IGNORED_FOR_DUPLICATE = re.compile(r"[\s.,!?·~…\-_'\"“”‘’]")
# 숫자 하나 (1,000이나 3.5처럼 쉼표·소수점이 낀 숫자도 하나로 본다)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


async def recommend_copies_for_images(
    recommender: CopyRecommender,
    images: list[str],
    prompt: str,
    requests: dict[CopyRole, str],
    job: GenerationJob | None = None,
) -> list[tuple[ImageCopies | None, str | None]]:
    """생성된 이미지마다 문구를 동시에 추천한다. 실패한 이미지가 있어도 나머지는 돌려준다.

    Args:
        recommender: 문구 추천기.
        images: PNG 이미지의 base64 문자열 목록.
        prompt: 사용자가 입력한 한국어 이미지 설명.
        requests: 역할별 문구 요청 (요청이 없는 역할은 키가 없다).
        job: 진행 상황을 기록하고 취소를 확인할 작업. 없으면 기록하지 않는다.

    Returns:
        list[tuple[ImageCopies | None, str | None]]: images 순서대로 (추천 문구, 에러 메시지).
            성공하면 (문구, None), 실패하면 (None, 화면에 보여줄 메시지).

    Raises:
        GenerationCancelledError: job이 취소되었을 때.
    """
    if job is not None:
        job.start_recommending_copy(len(images))

    async def recommend_one(image_base64: str) -> tuple[ImageCopies | None, str | None]:
        """이미지 한 장의 문구를 추천하고, 실패하면 에러 메시지로 바꾼다."""
        # 취소(CancelledError)는 잡지 않고 그대로 올려 보낸다. 끝난 장수에도 세지 않는다
        try:
            result = (
                await recommend_copies(recommender, image_base64, prompt, requests),
                None,
            )
        except CopyRecommendationError as error:
            logger.warning("문구 추천 실패: %s", error)
            result = None, COPY_RECOMMENDATION_FAILED_MESSAGE
        except Exception:
            logger.exception("문구 추천 중 예상하지 못한 오류")
            result = None, COPY_RECOMMENDATION_FAILED_MESSAGE
        if job is not None:
            job.report_copy_done()
        return result

    gathered = asyncio.gather(*(recommend_one(image) for image in images))
    if job is None:
        return list(await gathered)

    # 문구 추천은 OpenAI 응답을 기다리는 동안 취소를 확인할 지점이 없으므로
    # 취소 요청을 함께 기다리다가 먼저 오면 추천을 멈춘다
    cancel_waiter = asyncio.ensure_future(job.wait_cancelled())
    finished = False
    try:
        await asyncio.wait(
            {gathered, cancel_waiter}, return_when=asyncio.FIRST_COMPLETED
        )
        finished = gathered.done()
    finally:
        cancel_waiter.cancel()
        if not gathered.done():
            gathered.cancel()
            # 취소된 결과를 받아 두지 않으면 asyncio가 경고를 남긴다.
            # gather는 취소돼도 cancelled()가 아니라 CancelledError를 결과로 가지므로
            # 취소 여부는 finished로 판단한다
            with contextlib.suppress(asyncio.CancelledError):
                await gathered
    if not finished:
        raise GenerationCancelledError
    return list(gathered.result())


async def recommend_copies(
    recommender: CopyRecommender,
    image_base64: str,
    prompt: str,
    requests: dict[CopyRole, str],
) -> ImageCopies:
    """이미지 한 장에 대해 title, subtitle, text를 한 묶음으로 AI 문구 묶음을 추천한다.

    역할별 요청이 있으면 AI가 참고해 쓰고, 요청에 든 숫자를 바꾼 묶음은 버린다. 문구 배치
    추천에 쓸 강조색·글꼴 스타일과 이미지의 대표색도 함께 돌려준다.

    정리 후 개수가 모자라면 모자란 만큼 한 번 더 요청한다. 전체 시간은 COPY_TIMEOUT_SECONDS로
    제한하고, 재요청이 시간을 넘기면 앞서 받은 묶음만 돌려준다.

    Args:
        recommender: 문구 추천기.
        image_base64: PNG 이미지의 base64 문자열.
        prompt: 사용자가 입력한 한국어 이미지 설명.
        requests: 역할별 문구 요청 (요청이 없는 역할은 키가 없다).

    Returns:
        ImageCopies: 역할별 추천 문구 (역할마다 1~COPIES_PER_ROLE개, 같은 번호끼리 한 묶음)와
            강조색·스타일·대표색.

    Raises:
        CopyRecommendationError: 추천에 실패했거나, 쓸 수 있는 묶음이 하나도 없거나,
            이미지를 읽을 수 없을 때.
    """
    try:
        sets, accent, styles = await _collect_sets(
            recommender, image_base64, prompt, requests
        )
        palette = await run_in_threadpool(
            extract_palette, decode_base64_image(image_base64)
        )
    except ValueError as error:
        # 이미지를 읽을 수 없을 때 (to_jpeg_data_url, decode_base64_image)
        raise CopyRecommendationError(str(error)) from error
    if not sets:
        raise CopyRecommendationError("조건에 맞는 문구 묶음이 하나도 없습니다.")
    return ImageCopies(
        **{
            role: [CopySuggestion(text=copy_set[role]) for copy_set in sets]
            for role in COPY_ROLES
        },
        accent=accent,
        styles=styles,
        palette=palette,
    )


async def _collect_sets(
    recommender: CopyRecommender,
    image_base64: str,
    prompt: str,
    requests: dict[CopyRole, str],
) -> tuple[list[dict[CopyRole, str]], str | None, list[FontStyle]]:
    """COPIES_PER_ROLE개가 찰 때까지(최대 1번 재요청) AI 문구 묶음을 받아 정리한다.

    Returns:
        tuple[list[dict[CopyRole, str]], str | None, list[FontStyle]]: (정리·중복 제거한
            문구 묶음, 강조색 #RRGGBB 또는 None, 어울리는 순서의 글꼴 스타일).

    Raises:
        CopyRecommendationError: 추천기가 실패했거나, 첫 요청이 시간을 넘겼을 때.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + settings.copy_timeout_seconds
    accepted: list[dict[CopyRole, str]] = []
    accent = None
    styles: list[FontStyle] = []
    for _ in range(1 + _MAX_RETRIES):
        shortfall = COPIES_PER_ROLE - len(accepted)
        if shortfall <= 0:
            break
        try:
            result = await asyncio.wait_for(
                recommender.recommend(
                    image_base64,
                    prompt,
                    requests,
                    [dict(copy_set) for copy_set in accepted],
                    shortfall + _EXTRA_CANDIDATES,
                ),
                timeout=max(deadline - loop.time(), 0),
            )
        except TimeoutError as error:
            if not accepted:
                raise CopyRecommendationError(
                    f"{settings.copy_timeout_seconds}초 안에 문구 추천이 끝나지 "
                    "않았습니다."
                ) from error
            # 재요청이 시간을 넘겨도 앞서 받은 묶음은 버리지 않는다
            logger.warning(
                "문구 재요청 시간 초과. 받은 %d묶음만 돌려줍니다.", len(accepted)
            )
            break
        except CopyRecommendationError:
            if not accepted:
                raise
            logger.warning("문구 재요청 실패. 받은 %d묶음만 돌려줍니다.", len(accepted))
            break
        accent = accent or result.accent
        styles = styles or result.styles
        _accept_sets(result.sets, accepted, requests, prompt)
    return accepted[:COPIES_PER_ROLE], accent, styles


def _accept_sets(
    candidates: list[dict[CopyRole, str]],
    accepted: list[dict[CopyRole, str]],
    requests: dict[CopyRole, str],
    prompt: str,
) -> None:
    """후보 묶음을 정리해, 모든 역할이 쓸 수 있고 앞선 묶음과 겹치지 않는 묶음만 accepted에
    COPIES_PER_ROLE개까지 더한다.

    Args:
        candidates: 추천기가 돌려준 문구 묶음 (정리 전).
        accepted: 지금까지 받아 둔 묶음. 이 목록에 더한다.
        requests: 역할별 문구 요청.
        prompt: 사용자가 입력한 한국어 이미지 설명 (쓸 수 있는 숫자를 모을 때 쓴다).
    """
    seen = {
        role: {_duplicate_key(copy_set[role]) for copy_set in accepted}
        for role in COPY_ROLES
    }
    allowed_numbers = _numbers(" ".join([prompt, *requests.values()]))
    for raw in candidates:
        if len(accepted) >= COPIES_PER_ROLE:
            break
        copy_set = {role: _clean(raw[role]) for role in COPY_ROLES}
        keys = {role: _duplicate_key(copy_set[role]) for role in COPY_ROLES}
        if any(
            not _is_valid(copy_set[role], role, requests, allowed_numbers)
            or keys[role] in seen[role]
            for role in COPY_ROLES
        ):
            continue
        for role in COPY_ROLES:
            seen[role].add(keys[role])
        accepted.append(copy_set)


def _clean(text: str) -> str:
    """AI 문구의 앞뒤 공백·따옴표와 끝 마침표를 지우고 연속 공백을 하나로 줄인다.

    Returns:
        str: 정리한 문구.
    """
    text = " ".join(text.split()).strip(_QUOTE_CHARS + " ")
    return text.rstrip(".。").strip()


def _is_valid(
    text: str,
    role: CopyRole,
    requests: dict[CopyRole, str],
    allowed_numbers: set[str],
) -> bool:
    """정리한 AI 문구를 쓸 수 있는지 확인한다.

    Args:
        text: 정리한 문구.
        role: 역할.
        requests: 역할별 문구 요청.
        allowed_numbers: 이미지 설명과 요청에 든 숫자.

    Returns:
        bool: 아래를 모두 만족하면 True.
            - 비어 있지 않고 역할별 최대 글자 수 이하
            - 해시태그(#)가 없다. 그 역할의 요청에 #이 있으면 허용한다
            - 요청이 하나라도 있으면, 이미지 설명·요청에 없는 숫자를 쓰지 않는다
            - 그 역할에 요청이 있으면, 요청의 숫자를 모두 담는다 (가격·날짜를 바꾸지 않는다)
    """
    if not 0 < len(text) <= copy_max_length(role, requests):
        return False
    request = requests.get(role, "")
    if "#" in text and "#" not in request:
        return False
    numbers = _numbers(text)
    if requests and not numbers <= allowed_numbers:
        return False
    return _numbers(request) <= numbers


def _numbers(text: str) -> set[str]:
    """글에 든 숫자를 모은다. 쉼표는 지워 1,000과 1000을 같게 본다.

    Returns:
        set[str]: 숫자 문자열 집합.
    """
    return {match.replace(",", "") for match in _NUMBER.findall(text)}


def _duplicate_key(text: str) -> str:
    """공백·문장 부호·대소문자를 무시하고 비교하기 위한 키를 만든다.

    Returns:
        str: 중복 비교용 키.
    """
    return _IGNORED_FOR_DUPLICATE.sub("", text).lower()
