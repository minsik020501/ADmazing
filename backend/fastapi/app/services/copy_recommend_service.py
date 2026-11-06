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

logger = logging.getLogger(__name__)

# 길이 초과·중복으로 버려질 문구를 감안해 필요한 개수보다 더 받는다
_EXTRA_CANDIDATES = 2
# 정리 후에도 모자랄 때 모자란 만큼 다시 요청하는 횟수
_MAX_RETRIES = 1
# 문구 앞뒤에서 지우는 따옴표·괄호
_QUOTE_CHARS = "\"'“”‘’「」『』《》〈〉`"
# 중복 비교에서 무시하는 문자 (공백, 문장 부호)
_IGNORED_FOR_DUPLICATE = re.compile(r"[\s.,!?·~…\-_'\"“”‘’]")


async def recommend_copies_for_images(
    recommender: CopyRecommender,
    images: list[str],
    prompt: str,
    keywords: list[str],
    job: GenerationJob | None = None,
) -> list[tuple[ImageCopies | None, str | None]]:
    """생성된 이미지마다 문구를 동시에 추천한다. 실패한 이미지가 있어도 나머지는 돌려준다.

    Args:
        recommender: 문구 추천기.
        images: PNG 이미지의 base64 문자열 목록.
        prompt: 사용자가 입력한 한국어 이미지 설명.
        keywords: 모든 문구에 글자 그대로 넣어야 하는 필수 단어·문장.
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
                await recommend_copies(recommender, image_base64, prompt, keywords),
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
    keywords: list[str],
) -> ImageCopies:
    """이미지 한 장에 대해 역할마다 AI 문구를 추천한다.

    필수 단어가 있으면 모두 글자 그대로 들어간 문구만 남긴다. 문구 배치 추천에 쓸 강조색과
    글꼴 스타일도 함께 받는다.

    정리 후 개수가 모자라면 모자란 만큼 한 번 더 요청하고, 그래도 모자라면 있는 만큼 돌려준다.
    전체 시간은 COPY_TIMEOUT_SECONDS로 제한한다.

    Args:
        recommender: 문구 추천기.
        image_base64: PNG 이미지의 base64 문자열.
        prompt: 사용자가 입력한 한국어 이미지 설명.
        keywords: 모든 문구에 글자 그대로 넣어야 하는 필수 단어·문장.

    Returns:
        ImageCopies: 역할별 추천 문구 (역할마다 최대 COPIES_PER_ROLE개)와 강조색·스타일.

    Raises:
        CopyRecommendationError: 추천에 실패했거나, 시간을 넘겼거나, 이미지를 읽을 수 없을 때.
    """
    try:
        ai_copies, accent, styles = await asyncio.wait_for(
            _collect_ai_copies(recommender, image_base64, prompt, keywords),
            timeout=settings.copy_timeout_seconds,
        )
    except TimeoutError as error:
        raise CopyRecommendationError(
            f"{settings.copy_timeout_seconds}초 안에 문구 추천이 끝나지 않았습니다."
        ) from error
    except ValueError as error:
        # 이미지를 읽을 수 없을 때 (to_jpeg_data_url)
        raise CopyRecommendationError(str(error)) from error
    return _assemble(ai_copies, accent, styles)


async def _collect_ai_copies(
    recommender: CopyRecommender,
    image_base64: str,
    prompt: str,
    keywords: list[str],
) -> tuple[dict[CopyRole, list[str]], str | None, list[FontStyle]]:
    """필요한 개수가 찰 때까지(최대 1번 재요청) AI 문구를 받아 정리한다.

    Returns:
        tuple[dict[CopyRole, list[str]], str | None, list[FontStyle]]: (역할별로 정리·중복
            제거한 AI 문구, 강조색 #RRGGBB 또는 None, 어울리는 순서의 글꼴 스타일).

    Raises:
        CopyRecommendationError: 추천기가 실패했을 때.
    """
    accepted: dict[CopyRole, list[str]] = {role: [] for role in COPY_ROLES}
    accent = None
    styles: list[FontStyle] = []
    for _ in range(1 + _MAX_RETRIES):
        shortfall = {role: COPIES_PER_ROLE - len(accepted[role]) for role in COPY_ROLES}
        if all(count <= 0 for count in shortfall.values()):
            break
        existing = {role: list(accepted[role]) for role in COPY_ROLES}
        result = await recommender.recommend(
            image_base64,
            prompt,
            keywords,
            existing,
            {
                role: count + _EXTRA_CANDIDATES if count > 0 else 0
                for role, count in shortfall.items()
            },
        )
        accent = accent or result.accent
        styles = styles or result.styles
        for role in COPY_ROLES:
            if shortfall[role] <= 0:
                continue
            seen = {_duplicate_key(text) for text in existing[role]}
            added = 0
            for raw in result.copies.get(role, []):
                if added >= shortfall[role]:
                    break
                text = _clean(raw)
                key = _duplicate_key(text)
                if not _is_valid(text, role, keywords) or key in seen:
                    continue
                seen.add(key)
                accepted[role].append(text)
                added += 1
    return accepted, accent, styles


def _assemble(
    ai_copies: dict[CopyRole, list[str]], accent: str | None, styles: list[FontStyle]
) -> ImageCopies:
    """AI 문구를 역할별 COPIES_PER_ROLE개 이하로 묶는다.

    Returns:
        ImageCopies: 역할별 추천 문구와 강조색·스타일.
    """
    result = {}
    for role in COPY_ROLES:
        result[role] = [CopySuggestion(text=text) for text in ai_copies[role]][
            :COPIES_PER_ROLE
        ]
    return ImageCopies(**result, accent=accent, styles=styles)


def _clean(text: str) -> str:
    """AI 문구의 앞뒤 공백·따옴표와 끝 마침표를 지우고 연속 공백을 하나로 줄인다.

    Returns:
        str: 정리한 문구.
    """
    text = " ".join(text.split()).strip(_QUOTE_CHARS + " ")
    return text.rstrip(".。").strip()


def _is_valid(text: str, role: CopyRole, keywords: list[str]) -> bool:
    """정리한 AI 문구를 쓸 수 있는지 확인한다.

    Returns:
        bool: 비어 있지 않고, 역할별 최대 글자 수 이하이며, 해시태그가 없고,
            필수 단어가 모두 들어 있으면 True.
    """
    return (
        0 < len(text) <= copy_max_length(role, keywords)
        and "#" not in text
        and _contains_keywords(text, keywords)
    )


def _contains_keywords(text: str, keywords: list[str]) -> bool:
    """필수 단어가 모두 글자 그대로 들어 있는지 확인한다.

    띄어쓰기와 영문 대소문자는 무시한다 (예: "1+1 행사"와 "1+1행사"는 같다).

    Returns:
        bool: 모두 들어 있으면 True (필수 단어가 없으면 True).
    """
    compact = _compact(text)
    return all(_compact(keyword) in compact for keyword in keywords)


def _compact(text: str) -> str:
    """띄어쓰기를 지우고 소문자로 바꾼다.

    Returns:
        str: 비교용 문자열.
    """
    return "".join(text.split()).lower()


def _duplicate_key(text: str) -> str:
    """공백·문장 부호·대소문자를 무시하고 비교하기 위한 키를 만든다.

    Returns:
        str: 중복 비교용 키.
    """
    return _IGNORED_FOR_DUPLICATE.sub("", text).lower()
