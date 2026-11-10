"""OpenAI로 이미지를 보고 광고 문구 묶음과 문구 강조색·글꼴 스타일을 추천하는 문구 추천기.

강조색과 스타일은 문구 배치 추천(/api/layout/recommend)에서 쓴다. 강조색의 명도는 배치 추천이
글자 아래 배경을 보고 다시 맞추므로, 여기서는 색조와 채도(어떤 색인지)만 정하면 된다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import json
import re

from openai import OpenAIError

from app.core.config import settings
from app.core.copy_role import COPY_ROLES, CopyRole, copy_max_length
from app.core.layout_templates import FONT_STYLES, MAX_STYLES, FontStyle
from app.services.copy_candidates import CopyCandidates
from app.services.copy_recommendation_error import CopyRecommendationError
from app.services.openai_client import openai_client
from app.utils.image import to_jpeg_data_url

# 스타일을 고를 때 OpenAI에 알려 줄 스타일별 느낌과 어울리는 광고
_STYLE_GUIDES: dict[FontStyle, str] = {
    "minimal_gothic": "bold modern sans-serif; versatile, tech, fashion, everyday "
    "products",
    "serif": "elegant serif (myeongjo); premium, beauty, books, calm or emotional "
    "mood",
    "clean": "clean geometric headline with plain body; information-heavy, "
    "business, health, simple and trustworthy",
    "handwriting": "brush handwriting; warm, artisanal, traditional, homemade "
    "food, personal",
    "signature": "pixel/retro signature font; playful, game, retro, trendy youth",
    "impact_sale": "heavy impact gothic; sales, discounts, events, strong calls "
    "to action",
    "rounded": "soft rounded font; cute, kids, pets, cafe, desserts, friendly",
}

SYSTEM_PROMPT = (
    "You are a senior Korean advertising copywriter. You look at an advertisement "
    "image and its description, and write Korean ad copy that will be placed on "
    "top of the image.\n"
    "Roles:\n"
    "- title: the main headline. Short, punchy and memorable.\n"
    "- subtitle: supports the title with a concrete benefit or feeling.\n"
    "- text: body copy such as product information, offers or a call to action.\n"
    "You write copy as SETS. One set is one ad: its title, subtitle and text are "
    "shown together, so they must read naturally as a whole, share the same angle "
    "and tone, and not repeat each other. Different sets take clearly different "
    "angles.\n"
    "The maximum number of characters per line for each role is given in the "
    "request.\n"
    "Requests per role:\n"
    "- The user may give a request for some roles. A request is NOT the final "
    "copy. It tells you what that role should say. Rewrite it into good copy that "
    "fits the role and its character limit (e.g. a short headline for title, a "
    "benefit line for subtitle, an informative line for text).\n"
    "- Keep every fact in a request: never change, round or drop numbers, prices, "
    "dates, periods, percentages, names or places. Write numbers exactly as in the "
    "request.\n"
    "- Roles without a request are written freely, but must fit the same set and "
    "may use facts from the other requests.\n"
    "Rules:\n"
    "- Write in natural Korean. English words only when they are common in Korean "
    "ads (e.g. SALE, NEW).\n"
    "- Reflect what is actually visible in the image: the subject, colors, mood and "
    "season. Do not invent product names, prices, discounts, dates or other numbers "
    "that are neither in the image nor in the description, requests or existing "
    "sets.\n"
    "- Existing sets were already chosen. Match their tone, but never repeat them "
    "or write a near-duplicate.\n"
    "- No quotation marks, emojis, hashtags or trailing periods, unless the "
    "request itself contains them.\n"
    "- Return exactly the requested number of sets.\n"
    "Accent color:\n"
    "- Also choose ONE accent color (#RRGGBB) for the headline text on this image. "
    "Take it from the product or a key object, or choose a color that harmonizes "
    "with the mood. Avoid skin tones and dull grays; pick a color with clear hue.\n"
    "- Do not worry about contrast or lightness. Brightness is adjusted "
    "automatically for readability.\n"
    f"Font styles: choose 1 to {MAX_STYLES} styles that best fit this ad (image, "
    "mood, copy and requests), best first. Available styles:\n"
    + "".join(f"- {style}: {guide}\n" for style, guide in _STYLE_GUIDES.items())
)
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Structured Outputs(strict)는 모든 속성을 required로 두고 추가 속성을 막아야 한다
_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "ad_copies",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "sets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {role: {"type": "string"} for role in COPY_ROLES},
                        "required": list(COPY_ROLES),
                        "additionalProperties": False,
                    },
                },
                "accent": {"type": "string", "description": "#RRGGBB"},
                "styles": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(FONT_STYLES)},
                    "description": f"1~{MAX_STYLES} font styles, best first",
                },
            },
            "required": ["sets", "accent", "styles"],
            "additionalProperties": False,
        },
    },
}


class OpenAICopyRecommender:
    """OpenAI Structured Outputs로 문구 묶음과 강조색·글꼴 스타일을 JSON으로 받는다."""

    async def recommend(
        self,
        image_base64: str,
        prompt: str,
        requests: dict[CopyRole, str],
        existing: list[dict[CopyRole, str]],
        count: int,
    ) -> CopyCandidates:
        """이미지와 프롬프트, 역할별 요청, 이미 받은 묶음을 보내고 문구 묶음과 강조색·스타일을
        받는다.

        Args:
            image_base64: PNG 이미지의 base64 문자열.
            prompt: 사용자가 입력한 한국어 이미지 설명.
            requests: 역할별 문구 요청.
            existing: 앞서 받아 둔 문구 묶음.
            count: 필요한 문구 묶음 수.

        Returns:
            CopyCandidates: 문구 묶음 후보 (정리 전)와 강조색·스타일.

        Raises:
            CopyRecommendationError: OpenAI 호출이 실패했거나 응답 형식이 틀렸을 때.
        """
        image_url = to_jpeg_data_url(image_base64, settings.copy_image_max_side)
        try:
            response = await openai_client.chat.completions.create(
                model=settings.copy_openai_model or settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": _build_user_message(
                                    prompt, requests, existing, count
                                ),
                            },
                            {
                                "type": "image_url",
                                # 문구에는 분위기·색감·피사체만 필요해 저해상도로 보낸다
                                "image_url": {"url": image_url, "detail": "low"},
                            },
                        ],
                    },
                ],
                response_format=_RESPONSE_FORMAT,
                # 설치된 SDK가 reasoning_effort 인자를 모를 수 있어 본문에 직접 넣는다
                extra_body=(
                    {"reasoning_effort": settings.copy_reasoning_effort}
                    if settings.copy_reasoning_effort
                    else None
                ),
            )
        except OpenAIError as error:
            raise CopyRecommendationError(f"OpenAI 호출 실패: {error}") from error
        return _parse_response(response.choices[0].message.content)


def _build_user_message(
    prompt: str,
    requests: dict[CopyRole, str],
    existing: list[dict[CopyRole, str]],
    count: int,
) -> str:
    """이미지 설명, 역할별 요청, 이미 받은 묶음, 필요한 묶음 수, 역할별 최대 글자 수를 담은
    사용자 메시지를 만든다.

    Returns:
        str: OpenAI에 보낼 사용자 메시지.
    """
    lines = [f"Image description (Korean): {prompt}", "", "Requests per role:"]
    for role in COPY_ROLES:
        lines.append(
            f"- {role}: "
            + (
                json.dumps(requests[role], ensure_ascii=False)
                if role in requests
                else "none"
            )
        )
    lines += ["", "Maximum characters per line:"]
    for role in COPY_ROLES:
        lines.append(f"- {role}: {copy_max_length(role, requests)}")
    lines += [
        "",
        "Existing sets: " + json.dumps(existing, ensure_ascii=False),
        "",
        f"Number of new sets to write: {count}",
    ]
    return "\n".join(lines)


def _parse_response(content: str | None) -> CopyCandidates:
    """Structured Outputs 응답 JSON을 문구 묶음 목록과 강조색·스타일로 읽는다.

    Returns:
        CopyCandidates: 문구 묶음 후보와 강조색·스타일 (역할이 빠진 묶음과 형식이 틀린
            강조색은 버리고, 목록에 없는 스타일과 중복은 뺀다).

    Raises:
        CopyRecommendationError: 응답이 비었거나 형식이 틀렸을 때 (모델이 거절한 경우 포함).
    """
    if not content:
        raise CopyRecommendationError("OpenAI 응답이 비어 있습니다.")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as error:
        raise CopyRecommendationError("OpenAI 응답이 JSON이 아닙니다.") from error
    raw_sets = data.get("sets", [])
    if not isinstance(raw_sets, list):
        raise CopyRecommendationError("OpenAI 응답의 sets가 목록이 아닙니다.")
    sets: list[dict[CopyRole, str]] = [
        {role: item[role] for role in COPY_ROLES}
        for item in raw_sets
        if isinstance(item, dict)
        and all(isinstance(item.get(role), str) for role in COPY_ROLES)
    ]
    accent = data.get("accent")
    if not isinstance(accent, str) or not _HEX_COLOR.match(accent.strip()):
        accent = None
    styles: list[FontStyle] = []
    raw_styles = data.get("styles", [])
    for style in raw_styles if isinstance(raw_styles, list) else []:
        if style in FONT_STYLES and style not in styles:
            styles.append(style)
    return CopyCandidates(
        sets=sets,
        accent=accent.strip().upper() if accent else None,
        styles=styles[:MAX_STYLES],
    )
