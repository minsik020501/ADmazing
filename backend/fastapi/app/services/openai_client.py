"""번역과 문구 추천이 함께 쓰는 OpenAI 클라이언트.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from openai import AsyncOpenAI

from app.core.config import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
