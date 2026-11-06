"""광고 레이아웃 템플릿으로 문구 배치 추천안을 만드는 추천기.

모델이 좌표를 정하지 않고, 사람이 정한 템플릿(app/core/layout_templates.py) 중에서 고른다.
CPU에서만 돌며, 영역 찾기를 포함해 1초 안팎이다.

순서:
    1. 가리면 안 되는 영역(제품, 얼굴)을 찾는다 (검출기가 없으면 건너뛴다)
    2. 템플릿마다 문구 블록을 쌓아 보고, 영역을 8% 넘게 덮는 템플릿은 뺀다
    3. 글자가 놓일 자리에서 읽히는 글자색이 없는 문구가 적은 순서, 그다음 블록 아래 배경이
       차분한 순서로 최대 5개를 고른다. 안 덮는 템플릿이 3개보다 적으면 덮는 정도가 작은
       템플릿으로 3개까지 채운다
    4. 추천안마다 다른 글꼴 스타일과 배색 방식(layout_palette)을 쓴다. 강조색과 글꼴 스타일은
       문구 추천에서 OpenAI가 이미지를 보고 고른 값을 요청으로 받는다

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import logging

from PIL import Image

from app.core.layout_templates import (
    FONT_STYLES,
    FONT_SIZES,
    GAPS,
    LINE_HEIGHTS,
    MARGIN,
    TEMPLATES,
    FontStyle,
)
from app.schemas.layout_copy import LayoutCopy
from app.schemas.layout_proposal import LayoutProposal
from app.schemas.text_layer import TextLayer
from app.services.layout_palette import (
    SCHEME_NAMES,
    SCHEMES,
    accent_from_hex,
    apply_palette,
    busyness,
    is_readable,
    luminance_map,
    text_background,
    MIN_CONTRAST,
)
from app.services.subject_detector import Box, SubjectDetector, union_box
from app.utils.text_measure import box_size

logger = logging.getLogger(__name__)

# 블록이 가리면 안 되는 영역을 이보다 많이 덮으면 그 템플릿은 쓰지 않는다
MAX_SUBJECT_COVER = 0.08
# 안 덮는 템플릿이 이보다 적으면 덮는 템플릿으로 채운다
MIN_PROPOSALS = 3


class TemplateLayoutRecommender:
    """템플릿과 규칙으로 문구 배치 추천안을 만든다."""

    def __init__(self, detector: SubjectDetector | None) -> None:
        """추천기를 만든다.

        Args:
            detector: 영역 찾기 검출기. None이면 영역을 피하지 않는다 (개발용).
        """
        self._detector = detector

    def recommend(
        self,
        image: Image.Image,
        copies: list[LayoutCopy],
        num_proposals: int,
        accent: str | None = None,
        styles: list[FontStyle] | None = None,
    ) -> list[LayoutProposal]:
        """추천안을 만든다.

        Args:
            image: 원본 이미지.
            copies: 배치할 역할별 문구.
            num_proposals: 받을 최대 추천안 수.
            accent: 강조색 #RRGGBB (문구 추천 결과). 없으면 톤온톤으로만 추천한다.
            styles: 글꼴 스타일 (어울리는 순서, 문구 추천 결과). 추천안마다 앞에서부터 하나씩
                쓰고, 모자라면 FONT_STYLES 순서대로 나머지 스타일로 채운다.

        Returns:
            list[LayoutProposal]: 추천안 (MIN_PROPOSALS ~ num_proposals개, 템플릿 수 이하).
        """
        subjects = self._detect(image)
        subject = union_box([box for _, box in subjects])
        accent_lch = accent_from_hex(accent)
        style_order = list(dict.fromkeys([*(styles or []), *FONT_STYLES]))

        aspect = image.height / image.width
        luminance = luminance_map(image)
        candidates = []
        for template_id in TEMPLATES:
            layers = build_block(
                template_id, copies, FONT_STYLES[style_order[0]][:2], aspect, image
            )
            block = block_box(layers, aspect)
            cover = _cover(block, subject) if subject else 0.0
            unreadable = sum(
                not is_readable(
                    text_background(luminance, layer, aspect),
                    MIN_CONTRAST[layer.role],
                )
                for layer in layers
            )
            candidates.append(
                (
                    cover > MAX_SUBJECT_COVER,
                    cover,
                    unreadable,
                    busyness(image, block),
                    template_id,
                )
            )
        clean = sorted((c for c in candidates if not c[0]), key=lambda c: c[2:4])
        if len(clean) >= MIN_PROPOSALS:
            chosen = clean
        else:
            covering = sorted((c for c in candidates if c[0]), key=lambda c: c[1:4])
            chosen = (clean + covering)[:MIN_PROPOSALS]
        chosen = chosen[:num_proposals]

        proposals = []
        for index, (_, cover, unreadable, busy, template_id) in enumerate(chosen):
            heading, body, style_name = FONT_STYLES[
                style_order[index % len(style_order)]
            ]
            layers = build_block(template_id, copies, (heading, body), aspect, image)
            scheme = apply_palette(
                layers,
                image,
                luminance,
                block_box(layers, aspect),
                SCHEMES[index % len(SCHEMES)],
                accent_lch,
            )
            proposals.append(
                LayoutProposal(
                    label=f"{TEMPLATES[template_id].name} · {style_name}"
                    f" · {SCHEME_NAMES[scheme]}",
                    layers=layers,
                )
            )
            logger.debug(
                "template %s cover=%.0f%% unreadable=%d busy=%.0f",
                template_id,
                cover * 100,
                unreadable,
                busy,
            )
        return proposals

    def _detect(self, image: Image.Image) -> list[tuple[str, Box]]:
        """영역을 찾는다. 검출기가 없거나 실패하면 빈 목록이다.

        Returns:
            list[tuple[str, Box]]: 영역 목록.
        """
        if self._detector is None:
            return []
        try:
            return self._detector.detect(image)
        except Exception:
            # 영역을 못 찾아도 추천안은 만든다 (영역을 피하지 않을 뿐이다)
            logger.exception("영역 찾기 실패. 영역을 피하지 않고 추천합니다.")
            return []


def build_block(
    template_id: str,
    copies: list[LayoutCopy],
    fonts: tuple[str, str],
    aspect: float,
    image: Image.Image,
) -> list[TextLayer]:
    """템플릿 하나로 문구 블록을 쌓아 문구 상자 목록을 만든다. 색은 아직 정하지 않는다.

    Args:
        template_id: TEMPLATES의 키.
        copies: 역할별 문구.
        fonts: (제목 글꼴, 본문 글꼴).
        aspect: 이미지 세로 / 가로.
        image: 원본 이미지 (크기만 쓴다).

    Returns:
        list[TextLayer]: 위에서부터 쌓은 문구 상자들.
    """
    template = TEMPLATES[template_id]
    width, height = image.size
    short = min(width, height)
    margin_x, margin_y = MARGIN * short / width, MARGIN * short / height
    block_w = round(min(template.width * short / width, 1 - 2 * margin_x), 4)

    layers = [
        TextLayer(
            role=copy.role,
            text=copy.text,
            width=block_w,
            fontId=fonts[0] if copy.role == "title" else fonts[1],
            fontSize=round(FONT_SIZES[copy.role] * short / height, 4),
            bold=copy.role == "title",
            align=template.align,
            lineHeight=LINE_HEIGHTS[copy.role],
        )
        for copy in copies
    ]
    heights = [
        box_size(layer.text, layer.fontSize, aspect, block_w, layer.lineHeight)[1]
        for layer in layers
    ]
    gaps = [GAPS[layer.role] * layer.fontSize for layer in layers[:-1]]
    total = sum(heights) + sum(gaps)
    if template.anchor == "top":
        top = margin_y
    elif template.anchor == "bottom":
        top = 1 - margin_y - total
    else:
        top = 0.5 - total / 2

    if template.align == "left":
        x = margin_x + block_w / 2
    elif template.align == "right":
        x = 1 - margin_x - block_w / 2
    else:
        x = 0.5
    for index, layer in enumerate(layers):
        layer.x = round(x, 4)
        layer.y = round(min(max(top + heights[index] / 2, 0), 1), 4)
        top += heights[index] + (gaps[index] if index < len(gaps) else 0)
    return layers


def block_box(layers: list[TextLayer], aspect: float) -> Box:
    """블록 전체 영역을 어림한다.

    Returns:
        Box: (왼쪽, 위, 오른쪽, 아래) 비율.
    """
    boxes = []
    for layer in layers:
        w, h = box_size(
            layer.text, layer.fontSize, aspect, layer.width, layer.lineHeight
        )
        boxes.append(
            (layer.x - w / 2, layer.y - h / 2, layer.x + w / 2, layer.y + h / 2)
        )
    return union_box(boxes)


def _cover(block: Box, subject: Box) -> float:
    """블록 면적 중 영역과 겹친 비율.

    Returns:
        float: 0~1.
    """
    inter = max(0.0, min(block[2], subject[2]) - max(block[0], subject[0])) * max(
        0.0, min(block[3], subject[3]) - max(block[1], subject[1])
    )
    area = (block[2] - block[0]) * (block[3] - block[1])
    return inter / area if area > 0 else 0.0
