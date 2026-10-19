"""OpenAI API를 이용한 한국어 → 영어 프롬프트 번역 서비스.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-19
수정자: ven_choi
"""

from openai import AsyncOpenAI

from app.core.config import settings

SYSTEM_PROMPT = (
    "You translate Korean descriptions of advertisement images into English prompts "
    "for a text-to-image model. Keep every visual detail (subject, style, colors, "
    "composition, mood). Respond with the English prompt only, without quotes or "
    "explanations."
)

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def translate_to_english(text: str) -> str:
    """한국어 광고 이미지 설명을 이미지 생성용 영어 프롬프트로 번역한다.

    Args:
        text: 한국어 광고 이미지 설명.

    Returns:
        str: 번역된 영어 프롬프트.
    """
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content.strip()
