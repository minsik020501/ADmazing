"""모델 없이 고정 템플릿 추천안을 돌려주는 개발용 문구 배치 추천기.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import json
import time

from PIL import Image

from app.schemas.layout_copy import LayoutCopy

# 응답을 기다리는 화면을 확인할 수 있도록 흉내 내는 생성 시간
_MOCK_SECONDS = 0.5

# (라벨, 역할별 (x, y, size, font, color, align, effect, effect_color))
_TEMPLATES = [
    (
        "상단 헤드라인",
        {
            "title": (
                0.5,
                0.13,
                0.1,
                "black-han-sans",
                "#FFFFFF",
                "center",
                "stroke",
                "#000000",
            ),
            "subtitle": (
                0.5,
                0.24,
                0.05,
                "pretendard",
                "#FFFFFF",
                "center",
                "shadow",
                "#000000",
            ),
            "text": (
                0.5,
                0.88,
                0.04,
                "pretendard",
                "#FFFFFF",
                "center",
                "background",
                "#000000",
            ),
        },
    ),
    (
        "하단 정보형",
        {
            "title": (
                0.5,
                0.72,
                0.09,
                "gmarket-sans",
                "#FFFFFF",
                "center",
                "shadow",
                "#000000",
            ),
            "subtitle": (
                0.5,
                0.81,
                0.045,
                "suit",
                "#FFFFFF",
                "center",
                "shadow",
                "#000000",
            ),
            "text": (
                0.5,
                0.9,
                0.035,
                "suit",
                "#FFFFFF",
                "center",
                "background",
                "#000000",
            ),
        },
    ),
    (
        "왼쪽 정렬 매거진",
        {
            "title": (
                0.3,
                0.16,
                0.08,
                "maru-buri",
                "#FFFFFF",
                "left",
                "shadow",
                "#000000",
            ),
            "subtitle": (
                0.3,
                0.26,
                0.045,
                "noto-serif-kr",
                "#FFFFFF",
                "left",
                "none",
                "#000000",
            ),
            "text": (
                0.3,
                0.9,
                0.035,
                "pretendard",
                "#FFFFFF",
                "left",
                "none",
                "#000000",
            ),
        },
    ),
    (
        "부드러운 라운드",
        {
            "title": (
                0.5,
                0.2,
                0.09,
                "cafe24-surround",
                "#FFFFFF",
                "center",
                "stroke",
                "#333333",
            ),
            "subtitle": (
                0.5,
                0.3,
                0.045,
                "gowun-dodum",
                "#FFFFFF",
                "center",
                "shadow",
                "#000000",
            ),
            "text": (
                0.5,
                0.86,
                0.035,
                "gowun-dodum",
                "#333333",
                "center",
                "background",
                "#FFFFFF",
            ),
        },
    ),
    (
        "손글씨 감성",
        {
            "title": (
                0.5,
                0.15,
                0.1,
                "nanum-brush-script",
                "#FFFFFF",
                "center",
                "shadow",
                "#000000",
            ),
            "subtitle": (
                0.5,
                0.26,
                0.05,
                "nanum-barun-pen",
                "#FFFFFF",
                "center",
                "shadow",
                "#000000",
            ),
            "text": (
                0.5,
                0.9,
                0.04,
                "nanum-barun-pen",
                "#FFFFFF",
                "center",
                "shadow",
                "#000000",
            ),
        },
    ),
]
_KEYS = ("x", "y", "size", "font", "color", "align", "effect", "effect_color")


class MockLayoutRecommender:
    """요청 문구의 역할에 맞춰 고정 템플릿 5개를 압축 추천안 JSON으로 돌려준다."""

    def generate(
        self,
        image: Image.Image,
        copies: list[LayoutCopy],
        user_prompt: str,
        sample: bool = False,
    ) -> str:
        """고정 템플릿을 모델 출력과 같은 JSON 문자열로 만든다.

        Args:
            image: 사용하지 않는다.
            copies: 배치할 역할별 문구. 템플릿에서 이 역할만 넣는다.
            user_prompt: 사용하지 않는다.
            sample: 사용하지 않는다.

        Returns:
            str: 압축 추천안 JSON 문자열.
        """
        time.sleep(_MOCK_SECONDS)
        proposals = [
            {
                "label": label,
                "layers": [
                    {"role": copy.role, **dict(zip(_KEYS, layers[copy.role]))}
                    for copy in copies
                ],
            }
            for label, layers in _TEMPLATES
        ]
        return json.dumps({"proposals": proposals}, ensure_ascii=False)
