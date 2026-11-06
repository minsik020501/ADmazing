"""OpenAI로 이미지를 보고 광고 문구를 추천하는 문구 추천기.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import json

from openai import OpenAIError

from app.core.config import settings
from app.core.copy_role import AI_COPY_MAX_LENGTH, COPY_ROLES, CopyRole
from app.services.copy_recommendation_error import CopyRecommendationError
from app.services.openai_client import openai_client
from app.utils.image import to_jpeg_data_url

SYSTEM_PROMPT = (
    "You are a senior Korean advertising copywriter. You look at an advertisement "
    "image and its description, and write Korean ad copy that will be placed on "
    "top of the image.\n"
    "Roles:\n"
    "- title: the main headline. Short, punchy and memorable. "
    f"At most {AI_COPY_MAX_LENGTH['title']} characters.\n"
    "- subtitle: supports the title with a concrete benefit or feeling. "
    f"At most {AI_COPY_MAX_LENGTH['subtitle']} characters.\n"
    "- text: body copy such as product information, offers or a call to action. "
    f"At most {AI_COPY_MAX_LENGTH['text']} characters.\n"
    "Rules:\n"
    "- Write in natural Korean. English words only when they are common in Korean "
    "ads (e.g. SALE, NEW).\n"
    "- Reflect what is actually visible in the image: the subject, colors, mood and "
    "season. Do not invent product names, prices, discounts or features that are "
    "neither in the image nor in the description or existing copy.\n"
    "- Existing copy was already chosen. Match its tone and information, but never "
    "repeat it or write a near-duplicate.\n"
    "- Every line in a role must be clearly different from the others.\n"
    "- No quotation marks, emojis, hashtags or trailing periods.\n"
    "- Return exactly the requested number of lines for each role, and an empty "
    "list for roles that need 0."
)

# Structured Outputs(strict)는 모든 속성을 required로 두고 추가 속성을 막아야 한다
_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "ad_copies",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                role: {"type": "array", "items": {"type": "string"}}
                for role in COPY_ROLES
            },
            "required": list(COPY_ROLES),
            "additionalProperties": False,
        },
    },
}


class OpenAICopyRecommender:
    """OpenAI Structured Outputs로 역할별 문구를 JSON으로 받는다."""

    async def recommend(
        self,
        image_base64: str,
        prompt: str,
        existing: dict[CopyRole, list[str]],
        counts: dict[CopyRole, int],
    ) -> dict[CopyRole, list[str]]:
        """이미지와 프롬프트, 이미 정해진 문구를 보내고 역할별 문구를 받는다.

        Args:
            image_base64: PNG 이미지의 base64 문자열.
            prompt: 사용자가 입력한 한국어 이미지 설명.
            existing: 역할별로 이미 정해진 문구 (사용자 문장, 앞서 받은 AI 문구).
            counts: 역할별로 필요한 AI 문구 수.

        Returns:
            dict[CopyRole, list[str]]: 역할별 문구 후보 (정리 전).

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
                                "text": _build_user_message(prompt, existing, counts),
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
            )
        except OpenAIError as error:
            raise CopyRecommendationError(f"OpenAI 호출 실패: {error}") from error
        return _parse_response(response.choices[0].message.content)


def _build_user_message(
    prompt: str,
    existing: dict[CopyRole, list[str]],
    counts: dict[CopyRole, int],
) -> str:
    """이미지 설명, 이미 정해진 문구, 역할별 필요 개수를 담은 사용자 메시지를 만든다.

    Returns:
        str: OpenAI에 보낼 사용자 메시지.
    """
    lines = [f"Image description (Korean): {prompt}", "", "Existing copy:"]
    for role in COPY_ROLES:
        copies = existing.get(role, [])
        lines.append(f"- {role}: {json.dumps(copies, ensure_ascii=False)}")
    lines += ["", "Number of new lines to write:"]
    for role in COPY_ROLES:
        lines.append(f"- {role}: {counts.get(role, 0)}")
    return "\n".join(lines)


def _parse_response(content: str | None) -> dict[CopyRole, list[str]]:
    """Structured Outputs 응답 JSON을 역할별 문구 목록으로 읽는다.

    Returns:
        dict[CopyRole, list[str]]: 역할별 문구 후보.

    Raises:
        CopyRecommendationError: 응답이 비었거나 형식이 틀렸을 때 (모델이 거절한 경우 포함).
    """
    if not content:
        raise CopyRecommendationError("OpenAI 응답이 비어 있습니다.")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as error:
        raise CopyRecommendationError("OpenAI 응답이 JSON이 아닙니다.") from error
    result: dict[CopyRole, list[str]] = {}
    for role in COPY_ROLES:
        values = data.get(role, [])
        if not isinstance(values, list):
            raise CopyRecommendationError(f"OpenAI 응답의 {role}이 목록이 아닙니다.")
        result[role] = [value for value in values if isinstance(value, str)]
    return result
