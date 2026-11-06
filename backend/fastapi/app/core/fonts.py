"""광고용 글꼴 목록(fonts/manifest.json)을 읽는다.

문구 배치 추천 모델에 고를 수 있는 글꼴을 알려주고, 결과의 글꼴 id를 검사하는 데 쓴다.
FE의 frontend/src/constants/fonts.json도 같은 manifest에서 만들어진다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import json
import logging
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)

# FE 에디터의 기본 글꼴 (frontend/src/constants/editor.ts DEFAULT_FONT_ID)
DEFAULT_FONT_ID = "pretendard"

# manifest를 읽지 못했을 때도 추천이 동작하도록 두는 최소 목록
_FALLBACK_FONTS = [
    {
        "id": "gmarket-sans",
        "category": "headline",
        "mood": "깔끔하고 힘 있는 커머스 고딕",
    },
    {"id": "pretendard", "category": "body", "mood": "읽기 편한 기본 고딕"},
]


@lru_cache
def load_fonts() -> tuple[dict, ...]:
    """manifest에서 글꼴의 id, category, mood만 읽는다. 결과는 캐시한다.

    Returns:
        tuple[dict, ...]: {"id", "category", "mood"} 목록. manifest를 읽지 못하면 최소 목록.
    """
    path = settings.fonts_manifest_path
    try:
        fonts = json.loads(path.read_text(encoding="utf-8"))["fonts"]
        return tuple(
            {"id": font["id"], "category": font["category"], "mood": font["mood"]}
            for font in fonts
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        logger.warning("글꼴 목록을 읽지 못해 기본 글꼴만 씁니다: %s", path)
        return tuple(_FALLBACK_FONTS)


def font_ids() -> frozenset[str]:
    """고를 수 있는 글꼴 id 집합을 반환한다.

    Returns:
        frozenset[str]: 글꼴 id 집합.
    """
    return frozenset(font["id"] for font in load_fonts())
