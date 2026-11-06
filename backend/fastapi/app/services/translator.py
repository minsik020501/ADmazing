"""OpenAI API를 이용한 한국어 → 영어 프롬프트 번역 서비스.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from app.core.config import settings
from app.services.openai_client import openai_client

# 이미지 모델은 지시문을 따르지 않고, 프롬프트에 나온 단어를 그림으로 옮긴다.
# "no text"처럼 부정문으로 써도 text라는 단어 때문에 오히려 글자가 생기므로
# 글자를 떠올리게 하는 단어(poster, sign, 따옴표 속 문구 등)를 아예 빼고
# 글자가 없는 상태를 긍정형(plain, blank, unlabeled)으로 묘사하게 한다.
# 광고 문구는 이미지 생성 후 화면에서 따로 얹는다
SYSTEM_PROMPT = (
    "You translate Korean descriptions of advertisement images into English prompts "
    "for a text-to-image model. Keep every visual detail (subject, style, colors, "
    "composition, mood).\n"
    "The generated image must contain no written characters at all, because ad copy "
    "is added later. Follow these rules:\n"
    "- Drop any request for slogans, copy, brand names, logos, prices, captions or "
    "other lettering. Never put quoted strings in the prompt.\n"
    "- Do not use the words text, letters, words, font, typography, title, "
    "headline, label, sign, logo or watermark, even in negative form "
    "(e.g. never write 'no text').\n"
    "- Describe the scene as a photograph or illustration, not as a poster, banner, "
    "flyer, magazine cover, billboard or advertisement layout.\n"
    "- Describe products, packaging, screens and signboards as plain, blank and "
    "unlabeled, and backgrounds as clean.\n"
    "Respond with the English prompt only, without quotes or explanations."
)


async def translate_to_english(text: str) -> str:
    """한국어 광고 이미지 설명을 이미지 생성용 영어 프롬프트로 번역한다.

    Args:
        text: 한국어 광고 이미지 설명.

    Returns:
        str: 번역된 영어 프롬프트.
    """
    response = await openai_client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content.strip()
