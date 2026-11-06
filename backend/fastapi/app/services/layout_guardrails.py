"""문구 배치 모델의 압축 출력을 검사·보정해 문구 상자(TextLayer)로 펼친다.

모델 출력을 그대로 믿지 않고 아래 순서로 처리한다. 고친 내용은 fixes로 돌려줘
로그와 Step 3 지표(가드레일 전후 비교)에 쓴다.

1. 모르는 글꼴, 형식이 틀린 색, 범위 밖 숫자를 기본값·범위 안으로 맞춘다
2. 글꼴 크기와 글자 수로 상자 크기를 어림해, 너무 넓으면 줄바꿈 폭을 정하고
   이미지 밖으로 나가지 않게 옮긴다 (세로가 넘치면 글꼴 크기를 줄인다)
3. 제품 가림: 가리면 안 되는 영역(subject)을 많이 덮는 문구는 위·아래·왼쪽·오른쪽 중
   가장 가까운 빈 곳으로 옮긴다. subject가 이미지 대부분이면(장면 사진) 하지 않는다
4. 겹침: 세로로 쌓인 문구가 서로 겹치면 아래 문구를 내리고, 이미지 밖으로 나가면
   묶음 전체를 올린다
5. 정렬: 상자가 이미지 왼쪽에 있으면 left, 오른쪽이면 right, 가운데면 center로 맞추고,
   같은 쪽 문구끼리 왼쪽(오른쪽) 끝을 맞춘다
6. 상자 뒤 배경과 글자색의 대비가 낮고 효과가 없으면 외곽선을 붙인다
7. 요청 문구를 넣고, 모델이 빠뜨린 역할은 기본 위치에 채운다

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import itertools
import math
import re
import unicodedata

from PIL import Image, ImageStat

from app.core.copy_role import CopyRole
from app.core.fonts import DEFAULT_FONT_ID, font_ids
from app.schemas.layout_copy import LayoutCopy
from app.schemas.layout_proposal import LayoutProposal
from app.schemas.text_layer import TextLayer
from app.schemas.text_layer_background import TextLayerBackground
from app.schemas.text_layer_shadow import TextLayerShadow
from app.schemas.text_layer_stroke import TextLayerStroke
from app.services.layout_prompt import EFFECTS, size_guide

# 역할별 기본 글꼴 (모르는 글꼴 id가 왔을 때)
ROLE_DEFAULT_FONT: dict[CopyRole, str] = {
    "title": "gmarket-sans",
    "subtitle": DEFAULT_FONT_ID,
    "text": DEFAULT_FONT_ID,
}
# 모델이 역할을 빠뜨렸을 때 쓰는 기본 가운데 위치 (x, y)
ROLE_DEFAULT_POSITION: dict[CopyRole, tuple[float, float]] = {
    "title": (0.5, 0.15),
    "subtitle": (0.5, 0.27),
    "text": (0.5, 0.86),
}
# 상자와 이미지 가장자리 사이에 남길 여백 (이미지 대비)
EDGE_MARGIN = 0.03
# 한 줄이 이보다 넓으면 이 폭(이미지 가로 대비)에서 줄을 바꾼다
WRAP_WIDTH = 0.8
# 글자색과 배경의 WCAG 대비비가 이보다 낮으면 효과를 붙인다
MIN_CONTRAST = 3.0
# 문구 상자 면적 중 이 비율보다 많이 subject를 덮으면 옮긴다
SUBJECT_COVER_LIMIT = 0.15
# subject가 이미지 면적의 이 비율보다 크면 장면 사진으로 보고 옮기지 않는다 (옮길 곳이 없다)
SCENE_SUBJECT_AREA = 0.6
# subject와 문구, 문구와 문구 사이에 둘 최소 간격 (이미지 대비)
GAP = 0.015
# subject 옆으로 옮길 때 문구를 접어 넣을 수 있는 최소 폭 (이미지 가로 대비)
MIN_SIDE_WIDTH = 0.2
# 글자 폭은 글자 수로 어림하므로 실제 글꼴보다 좁을 수 있다. 겹침·가림을 볼 때만 이만큼 키워 본다
BOX_SAFETY = 1.1
# 상자 가운데가 이 값보다 왼쪽이면 left, (1 - 이 값)보다 오른쪽이면 right 정렬로 본다
SIDE_ALIGN_THRESHOLD = 0.4
# left/right 정렬 문구에 고정할 상자 폭 (어림한 글자 폭 대비). FE에서 상자 끝을 정확히
# 맞추려고 폭을 고정하는데, 실제 글꼴이 더 넓어 줄이 바뀌지 않도록 여유를 둔다
ALIGN_BOX_SAFETY = 1.15
# subject 옆 좁은 칸에 접어 넣을 때 역할별 최대 줄 수. 넘으면 글자를 줄인다
SIDE_MAX_LINES: dict[CopyRole, int] = {"title": 2, "subtitle": 2, "text": 3}
# 옆 칸에 넣으려고 글자를 줄일 때의 하한 (역할별 권장 최소 크기 대비)
SIDE_MIN_SIZE_RATIO = 0.8
# 글꼴 크기 범위 (docs/text_layer_spec.md)
_FONT_SIZE_RANGE = (0.01, 0.4)
_LINE_HEIGHT = 1.2
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_MAX_LABEL_LENGTH = 20
# 대비를 잴 때 이미지를 줄이는 크기 (속도용)
_CONTRAST_SAMPLE_SIDE = 256


def build_proposals(
    raw_proposals: list[dict],
    copies: list[LayoutCopy],
    image: Image.Image,
    num_proposals: int,
    subject: tuple[float, float, float, float] | None = None,
) -> tuple[list[LayoutProposal], list[str]]:
    """모델의 압축 추천안을 검사·보정해 문구 상자 추천안으로 만든다.

    Args:
        raw_proposals: 모델 출력에서 꺼낸 추천안 목록 (layout_output_parser).
        copies: 요청한 역할별 문구.
        image: 원본 이미지. 비율과 배경 밝기를 보는 데 쓴다.
        num_proposals: 돌려줄 최대 추천안 수.
        subject: 가리면 안 되는 영역 (왼쪽, 위, 오른쪽, 아래 비율). 없으면 제품 가림
            보정을 하지 않는다.

    Returns:
        tuple[list[LayoutProposal], list[str]]: 추천안 목록과 고친 내용 목록.
            고친 내용은 "p1.title: unknown font 'abc'"처럼 추천안 순번과 역할을 붙인다.
    """
    sample = image.convert("RGB")
    sample.thumbnail((_CONTRAST_SAMPLE_SIDE, _CONTRAST_SAMPLE_SIDE))
    aspect = image.height / image.width
    proposals: list[LayoutProposal] = []
    fixes: list[str] = []
    if subject is not None and _area(subject) > SCENE_SUBJECT_AREA:
        fixes.append(f"subject covers {_area(subject):.0%} of image, not avoided")
        subject = None
    for index, raw in enumerate(raw_proposals[:num_proposals], start=1):
        prefix = f"p{index}"
        raw_layers = raw.get("layers")
        if not isinstance(raw_layers, list):
            fixes.append(f"{prefix}: layers missing, dropped")
            continue
        by_role = _layers_by_role(raw_layers, prefix, fixes)
        drafts = []
        for copy in copies:
            raw_layer = by_role.get(copy.role)
            if raw_layer is None:
                fixes.append(f"{prefix}.{copy.role}: missing, default position")
                raw_layer = {}
            drafts.append(
                _draft_layer(
                    raw_layer, copy, aspect, sample, f"{prefix}.{copy.role}", fixes
                )
            )
        if subject is not None:
            for draft in drafts:
                _avoid_subject(
                    draft, subject, aspect, f"{prefix}.{draft['role']}", fixes
                )
        _separate_stack(drafts, aspect, subject, prefix, fixes)
        _align_by_position(drafts, aspect, prefix, fixes)
        layers = [
            _finish_layer(draft, aspect, sample, f"{prefix}.{draft['role']}", fixes)
            for draft in drafts
        ]
        label = raw.get("label")
        if not isinstance(label, str) or not label.strip():
            label = f"추천안 {index}"
            fixes.append(f"{prefix}: label missing")
        proposals.append(
            LayoutProposal(label=label.strip()[:_MAX_LABEL_LENGTH], layers=layers)
        )
    return proposals, fixes


def _layers_by_role(raw_layers: list, prefix: str, fixes: list[str]) -> dict[str, dict]:
    """모델 출력 레이어를 역할별로 모은다. 같은 역할이 여러 번이면 첫 번째만 쓴다.

    Returns:
        dict[str, dict]: 역할 → 레이어 dict.
    """
    by_role: dict[str, dict] = {}
    for raw_layer in raw_layers:
        if not isinstance(raw_layer, dict):
            continue
        role = raw_layer.get("role")
        if role in by_role:
            fixes.append(f"{prefix}.{role}: duplicate role, dropped")
            continue
        by_role[role] = raw_layer
    return by_role


def _draft_layer(
    raw: dict,
    copy: LayoutCopy,
    aspect: float,
    sample: Image.Image,
    prefix: str,
    fixes: list[str],
) -> dict:
    """압축 레이어 하나의 값을 검사하고 이미지 안으로 맞춘 초안을 만든다.

    제품 가림·겹침 보정은 추천안 단위로 하므로 여기서는 하지 않는다.

    Args:
        raw: 모델 출력 레이어 ({role, x, y, size, font, color, align, effect, effect_color}).
        copy: 이 역할의 요청 문구.
        aspect: 이미지 세로 / 가로.
        sample: 대비 계산용으로 줄인 RGB 이미지.
        prefix: 고친 내용 앞에 붙일 위치 표시.
        fixes: 고친 내용을 추가할 목록.

    Returns:
        dict: {role, text, x, y, size, wrap, font, color, align, effect, effect_color}.
    """
    role = copy.role
    default_x, default_y = ROLE_DEFAULT_POSITION[role]
    default_size = sum(size_guide(role, sample.width, sample.height)) / 2

    font = raw.get("font")
    if font not in font_ids():
        if raw:
            fixes.append(f"{prefix}: unknown font {font!r}")
        font = ROLE_DEFAULT_FONT[role]
    color = _color(raw.get("color"), "#FFFFFF", f"{prefix}.color", fixes, bool(raw))
    align = raw.get("align")
    if align not in ("left", "center", "right"):
        if raw:
            fixes.append(f"{prefix}: invalid align {align!r}")
        align = "center"
    effect = raw.get("effect")
    if effect not in EFFECTS:
        if raw and effect is not None:
            fixes.append(f"{prefix}: invalid effect {effect!r}")
        effect = "none"
    effect_color = _color(
        raw.get("effect_color"),
        _contrasting(color),
        f"{prefix}.effect_color",
        fixes,
        False,
    )

    size = _number(
        raw.get("size"),
        default_size,
        _FONT_SIZE_RANGE,
        f"{prefix}.size",
        fixes,
        bool(raw),
    )
    x = _number(raw.get("x"), default_x, (0, 1), f"{prefix}.x", fixes, bool(raw))
    y = _number(raw.get("y"), default_y, (0, 1), f"{prefix}.y", fixes, bool(raw))

    # 모델이 정한 위아래 순서. 옮긴 뒤 겹침을 풀 때 이 순서로 쌓는다
    order = y
    x, y, size, wrap = _fit_inside(copy.text, x, y, size, aspect, prefix, fixes)
    return {
        "order": order,
        # 옆 칸에 넣으려고 줄일 수 있는 최소 글자 크기
        "min_size": size_guide(role, sample.width, sample.height)[0]
        * SIDE_MIN_SIZE_RATIO,
        "role": role,
        "text": copy.text,
        "x": x,
        "y": y,
        "size": size,
        "wrap": wrap,
        "font": font,
        "color": color,
        "align": align,
        "effect": effect,
        "effect_color": effect_color,
    }


def _finish_layer(
    draft: dict, aspect: float, sample: Image.Image, prefix: str, fixes: list[str]
) -> TextLayer:
    """초안의 대비를 확인하고 문구 상자로 펼친다.

    Args:
        draft: _draft_layer가 만들고 제품 가림·겹침 보정을 거친 초안.
        aspect: 이미지 세로 / 가로.
        sample: 대비 계산용으로 줄인 RGB 이미지.
        prefix: 고친 내용 앞에 붙일 위치 표시.
        fixes: 고친 내용을 추가할 목록.

    Returns:
        TextLayer: 문구 상자.
    """
    effect, effect_color = draft["effect"], draft["effect_color"]
    if effect == "none":
        ratio = _contrast_ratio(
            draft["color"], _mean_color(sample, _draft_box(draft, aspect))
        )
        if ratio < MIN_CONTRAST:
            fixes.append(f"{prefix}: low contrast {ratio:.1f}, stroke added")
            effect = "stroke"
            effect_color = _contrasting(draft["color"])

    return TextLayer(
        role=draft["role"],
        text=draft["text"],
        x=round(draft["x"], 4),
        y=round(draft["y"], 4),
        width=draft["wrap"],
        fontId=draft["font"],
        fontSize=round(draft["size"], 4),
        align=draft["align"],
        lineHeight=_LINE_HEIGHT,
        color=draft["color"],
        stroke=TextLayerStroke(color=effect_color) if effect == "stroke" else None,
        shadow=TextLayerShadow(color=effect_color) if effect == "shadow" else None,
        background=(
            TextLayerBackground(color=effect_color) if effect == "background" else None
        ),
    )


def _avoid_subject(
    draft: dict,
    subject: tuple[float, float, float, float],
    aspect: float,
    prefix: str,
    fixes: list[str],
) -> None:
    """초안이 subject를 많이 덮으면 위·아래·왼쪽·오른쪽 중 가장 가까운 빈 곳으로 옮긴다.

    왼쪽·오른쪽은 빈 폭이 MIN_SIDE_WIDTH 이상이면 그 폭에 맞춰 줄을 바꿔 넣는다.
    옮길 곳이 이미지 안에 없으면 그대로 두고 고친 내용에 남긴다.

    Args:
        draft: 문구 초안. x, y, wrap을 바꾼다.
        subject: 가리면 안 되는 영역 (비율).
        aspect: 이미지 세로 / 가로.
        prefix: 고친 내용 앞에 붙일 위치 표시.
        fixes: 고친 내용을 추가할 목록.
    """
    box = _draft_box(draft, aspect)
    cover = _intersection(box, subject) / max(_area(box), 1e-9)
    if cover <= SUBJECT_COVER_LIMIT:
        return
    x, y, wrap = draft["x"], draft["y"], draft["wrap"]
    left, top, right, bottom = subject

    # (x, y, 줄바꿈 폭, 글자 크기) 후보
    size = draft["size"]
    candidates = []
    width, height = _safe_size(draft, aspect, wrap)
    candidates.append((x, top - GAP - height / 2, wrap, size))  # 위
    candidates.append((x, bottom + GAP + height / 2, wrap, size))  # 아래
    for side_width, place in (
        (left - GAP - EDGE_MARGIN, lambda w: left - GAP - w / 2),  # 왼쪽
        (1 - EDGE_MARGIN - right - GAP, lambda w: right + GAP + w / 2),  # 오른쪽
    ):
        fitted = _fit_side(draft, aspect, side_width)
        if fitted is None:
            continue
        side_wrap, side_size = fitted
        side_w, side_h = _safe_size({**draft, "size": side_size}, aspect, side_wrap)
        cy = min(max(y, EDGE_MARGIN + side_h / 2), 1 - EDGE_MARGIN - side_h / 2)
        candidates.append((place(side_w), cy, side_wrap, side_size))

    inside = [
        (cx, cy, cwrap, csize)
        for cx, cy, cwrap, csize in candidates
        if _inside_image(cx, cy, *_safe_size({**draft, "size": csize}, aspect, cwrap))
    ]
    if not inside:
        fixes.append(f"{prefix}: covers subject {cover:.0%}, no room to move")
        return
    new_x, new_y, new_wrap, new_size = min(
        inside, key=lambda c: math.dist(c[:2], (x, y))
    )
    draft.update(x=new_x, y=new_y, wrap=new_wrap, size=new_size)
    fixes.append(
        f"{prefix}: covers subject {cover:.0%}, moved ({x:.2f}, {y:.2f}) -> "
        f"({new_x:.2f}, {new_y:.2f})"
        + (f", wrapped at {new_wrap}" if new_wrap != wrap else "")
        + (f", size {size:.3f} -> {new_size:.3f}" if new_size != size else "")
    )


def _fit_side(
    draft: dict, aspect: float, side_width: float
) -> tuple[float | None, float] | None:
    """subject 옆 칸(폭 side_width)에 문구를 넣을 줄바꿈 폭과 글자 크기를 정한다.

    한 줄로 들어가면 그대로 둔다. 넘치면 칸 폭에서 줄을 바꾸고, 역할별 최대 줄 수
    (SIDE_MAX_LINES)를 넘으면 글자를 줄인다. 최소 크기(min_size)로도 안 되면 넣지 않는다.

    Returns:
        tuple[float | None, float] | None: (줄바꿈 폭, 글자 크기). 넣을 수 없으면 None.
    """
    if side_width < MIN_SIDE_WIDTH:
        return None
    if _safe_size(draft, aspect, draft["wrap"])[0] <= side_width:
        return draft["wrap"], draft["size"]
    wrap = round(side_width / BOX_SAFETY, 4)
    # 한 줄로 썼을 때의 폭이 max_lines × 칸 폭 안에 들도록 글자 크기를 정한다
    one_line_width = _box_size(draft["text"], draft["size"], aspect)[0]
    max_lines = SIDE_MAX_LINES[draft["role"]]
    size = min(draft["size"], draft["size"] * wrap * max_lines / one_line_width)
    # 글자 단위 줄바꿈의 여유분 (한 줄에 다 못 채우는 칸)
    size *= 0.9
    if size < draft["min_size"]:
        return None
    return wrap, round(size, 4)


def _separate_stack(
    drafts: list[dict],
    aspect: float,
    subject: tuple[float, float, float, float] | None,
    prefix: str,
    fixes: list[str],
) -> None:
    """서로 겹치거나 GAP보다 가까운 문구 묶음을 모델이 정한 위아래 순서대로 다시 쌓는다.

    묶음이 subject와 가로로 겹치면 subject 바로 위나 바로 아래 중 묶음이 다 들어가는
    가까운 쪽에 쌓는다. 그 밖에는 묶음의 맨 위에서부터 아래로 쌓는다. 이미지 밖으로
    나가면 묶음을 안쪽으로 옮긴다.

    Args:
        drafts: 한 추천안의 문구 초안들. y를 바꾼다.
        aspect: 이미지 세로 / 가로.
        subject: 가리면 안 되는 영역. 없으면 None.
        prefix: 고친 내용 앞에 붙일 위치 표시.
        fixes: 고친 내용을 추가할 목록.
    """
    for group in _collision_groups(drafts, aspect):
        group.sort(key=lambda draft: draft["order"])
        heights = [_safe_size(d, aspect, d["wrap"])[1] for d in group]
        boxes = [_draft_box(d, aspect) for d in group]
        total = sum(heights) + GAP * (len(group) - 1)
        top, bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
        center = (top + bottom) / 2
        start = top
        if subject is not None and any(
            _overlaps_horizontally(box, subject) for box in boxes
        ):
            # subject 바로 위 또는 바로 아래에 묶음이 다 들어가는 쪽 중 가까운 쪽에 쌓는다
            options = [
                option
                for option in (
                    min(bottom, subject[1] - GAP) - total,  # 위
                    max(top, subject[3] + GAP),  # 아래
                )
                if EDGE_MARGIN <= option and option + total <= 1 - EDGE_MARGIN
            ]
            if options:
                start = min(options, key=lambda o: abs(o + total / 2 - center))
            else:
                fixes.append(f"{prefix}: no room above or below subject for lines")
        start = max(min(start, 1 - EDGE_MARGIN - total), EDGE_MARGIN)
        for draft, height in zip(group, heights):
            draft["y"] = start + height / 2
            start += height + GAP
        fixes.append(
            f"{prefix}: lines overlapped, restacked "
            + ", ".join(f"{d['role']} y={d['y']:.2f}" for d in group)
        )


def _align_by_position(
    drafts: list[dict], aspect: float, prefix: str, fixes: list[str]
) -> None:
    """상자 위치에 따라 정렬을 정하고, 같은 쪽 문구끼리 가장자리를 맞춘다.

    - 상자 가운데가 SIDE_ALIGN_THRESHOLD보다 왼쪽이면 left, 오른쪽 대칭이면 right,
      그 사이면 center.
    - left 문구들은 그중 가장 왼쪽 끝에, right 문구들은 가장 오른쪽 끝에 맞춘다.
    - FE에서 x는 상자 가운데이고 width가 없으면 실제 글자 폭으로 상자가 정해져 끝을 맞출 수
      없다. 그래서 left/right 문구는 width를 고정해 상자 끝이 정확히 그 위치에 오게 한다.

    Args:
        drafts: 한 추천안의 문구 초안들. align, x, wrap을 바꾼다.
        aspect: 이미지 세로 / 가로.
        prefix: 고친 내용 앞에 붙일 위치 표시.
        fixes: 고친 내용을 추가할 목록.
    """
    sides: dict[str, list[dict]] = {"left": [], "right": []}
    for draft in drafts:
        box = _draft_box(draft, aspect)
        center = (box[0] + box[2]) / 2
        if center < SIDE_ALIGN_THRESHOLD:
            align = "left"
        elif center > 1 - SIDE_ALIGN_THRESHOLD:
            align = "right"
        else:
            align = "center"
        if align != draft["align"]:
            fixes.append(
                f"{prefix}.{draft['role']}: align {draft['align']} -> {align} "
                f"(box center x={center:.2f})"
            )
            draft["align"] = align
        if align in sides:
            sides[align].append(draft)

    usable = 1 - 2 * EDGE_MARGIN
    for side, group in sides.items():
        if not group:
            continue
        widths = {
            id(draft): min(
                draft["wrap"]
                or _box_size(draft["text"], draft["size"], aspect)[0]
                * ALIGN_BOX_SAFETY,
                usable,
            )
            for draft in group
        }
        if side == "left":
            edge = max(EDGE_MARGIN, min(d["x"] - widths[id(d)] / 2 for d in group))
        else:
            edge = min(1 - EDGE_MARGIN, max(d["x"] + widths[id(d)] / 2 for d in group))
        for draft in group:
            width = round(widths[id(draft)], 4)
            draft["wrap"] = width
            draft["x"] = edge + width / 2 if side == "left" else edge - width / 2
            # 여백 밖으로 나가지 않게 한 번 더 맞춘다
            draft["x"] = min(
                max(draft["x"], EDGE_MARGIN + width / 2), 1 - EDGE_MARGIN - width / 2
            )


def _collision_groups(drafts: list[dict], aspect: float) -> list[list[dict]]:
    """가로로 겹치면서 세로 간격이 GAP보다 좁은 문구끼리 묶는다 (이어진 것까지 한 묶음).

    Returns:
        list[list[dict]]: 2개 이상인 묶음 목록.
    """
    parent = list(range(len(drafts)))

    def find(index: int) -> int:
        """묶음 대표를 찾는다."""
        while parent[index] != index:
            index = parent[index]
        return index

    boxes = [_draft_box(draft, aspect) for draft in drafts]
    for i, j in itertools.combinations(range(len(drafts)), 2):
        a, b = boxes[i], boxes[j]
        vertical_gap = max(a[1], b[1]) - min(a[3], b[3])
        if _overlaps_horizontally(a, b) and vertical_gap < GAP:
            parent[find(i)] = find(j)
    groups: dict[int, list[dict]] = {}
    for index, draft in enumerate(drafts):
        groups.setdefault(find(index), []).append(draft)
    return [group for group in groups.values() if len(group) > 1]


def _safe_size(draft: dict, aspect: float, wrap: float | None) -> tuple[float, float]:
    """겹침·가림을 볼 때 쓰는 여유 있는 상자 크기를 구한다 (BOX_SAFETY배).

    Returns:
        tuple[float, float]: (폭, 높이) 비율.
    """
    width, height = _box_size(draft["text"], draft["size"], aspect, wrap)
    return width * BOX_SAFETY, height * BOX_SAFETY


def _inside_image(x: float, y: float, width: float, height: float) -> bool:
    """가운데가 (x, y)인 상자가 여백 안쪽에 들어가는지 확인한다.

    Returns:
        bool: 들어가면 True.
    """
    eps = 1e-9
    return (
        EDGE_MARGIN + width / 2 - eps <= x <= 1 - EDGE_MARGIN - width / 2 + eps
        and EDGE_MARGIN + height / 2 - eps <= y <= 1 - EDGE_MARGIN - height / 2 + eps
    )


def _draft_box(draft: dict, aspect: float) -> tuple[float, float, float, float]:
    """초안의 여유 있는 상자 (왼쪽, 위, 오른쪽, 아래)를 구한다 (BOX_SAFETY배).

    Returns:
        tuple[float, float, float, float]: 상자 좌표 (비율, 이미지 밖이면 0~1을 넘는다).
    """
    width, height = _safe_size(draft, aspect, draft["wrap"])
    return (
        draft["x"] - width / 2,
        draft["y"] - height / 2,
        draft["x"] + width / 2,
        draft["y"] + height / 2,
    )


def _overlaps_horizontally(a, b) -> bool:
    """두 상자가 가로로 겹치는지 확인한다.

    Returns:
        bool: 가로 범위가 겹치면 True.
    """
    return min(a[2], b[2]) > max(a[0], b[0])


def _area(box) -> float:
    """상자 넓이를 구한다.

    Returns:
        float: 넓이 (비율²).
    """
    return max(box[2] - box[0], 0) * max(box[3] - box[1], 0)


def _intersection(a, b) -> float:
    """두 상자가 겹치는 넓이를 구한다.

    Returns:
        float: 넓이 (비율²).
    """
    return _area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def _number(
    value,
    default: float,
    bounds: tuple[float, float],
    name: str,
    fixes: list[str],
    report: bool,
) -> float:
    """숫자를 읽어 범위 안으로 맞춘다. 숫자가 아니면 기본값을 쓴다.

    Returns:
        float: 범위 안의 숫자.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if report:
            fixes.append(f"{name}: not a number {value!r}")
        return default
    low, high = bounds
    if not low <= value <= high:
        fixes.append(f"{name}: {value} out of range")
        return min(max(float(value), low), high)
    return float(value)


def _color(value, default: str, name: str, fixes: list[str], report: bool) -> str:
    """#RRGGBB 색을 읽는다. 형식이 틀리면 기본값을 쓴다.

    Returns:
        str: 대문자 #RRGGBB.
    """
    if isinstance(value, str) and _HEX_COLOR.match(value):
        return value.upper()
    if report:
        fixes.append(f"{name}: invalid color {value!r}")
    return default


def _fit_inside(
    text: str,
    x: float,
    y: float,
    size: float,
    aspect: float,
    prefix: str,
    fixes: list[str],
) -> tuple[float, float, float, float | None]:
    """상자가 이미지(여백 포함) 안에 들어가도록 줄바꿈 폭을 정하고 가운데 위치를 옮긴다.

    한 줄로 WRAP_WIDTH보다 넓으면 글자를 줄이지 않고 줄바꿈 폭(width)을 정해 여러 줄로 만든다.
    줄바꿈 후에도 세로가 넘치면 그때 글꼴 크기를 줄인다.

    Returns:
        tuple[float, float, float, float | None]: 보정한 (x, y, 글꼴 크기, 줄바꿈 폭).
            줄바꿈 폭이 None이면 한 줄(또는 \\n에서만 줄바꿈)이다.
    """
    usable = 1 - 2 * EDGE_MARGIN
    wrap = None
    width, height = _box_size(text, size, aspect, wrap)
    if width > WRAP_WIDTH:
        wrap = WRAP_WIDTH
        width, height = _box_size(text, size, aspect, wrap)
        fixes.append(f"{prefix}: too wide, wrapped at width {wrap}")
    if height > usable:
        size = max(size * usable / height, _FONT_SIZE_RANGE[0])
        width, height = _box_size(text, size, aspect, wrap)
        fixes.append(f"{prefix}: too tall, size reduced to {size:.3f}")

    fitted_x = _clamp_center(x, width)
    fitted_y = _clamp_center(y, height)
    if abs(fitted_x - x) > 1e-6 or abs(fitted_y - y) > 1e-6:
        fixes.append(
            f"{prefix}: outside image, moved ({x:.2f}, {y:.2f}) -> "
            f"({fitted_x:.2f}, {fitted_y:.2f})"
        )
    return fitted_x, fitted_y, size, wrap


def _clamp_center(center: float, length: float) -> float:
    """길이가 length인 상자의 가운데를 여백 안쪽 범위로 맞춘다.

    Returns:
        float: 보정한 가운데 위치.
    """
    low = EDGE_MARGIN + length / 2
    high = 1 - EDGE_MARGIN - length / 2
    if low > high:
        return 0.5
    return min(max(center, low), high)


def _box_size(
    text: str, size: float, aspect: float, wrap: float | None = None
) -> tuple[float, float]:
    """글자 수와 글꼴 크기로 상자 크기를 어림한다 (실제 글꼴 폭은 글꼴마다 다르다).

    Args:
        text: 문구 (줄바꿈 \\n 포함 가능).
        size: 글꼴 크기 (이미지 세로 대비).
        aspect: 이미지 세로 / 가로.
        wrap: 줄바꿈 폭 (이미지 가로 대비). None이면 \\n에서만 줄을 바꾼다.

    Returns:
        tuple[float, float]: (이미지 가로 대비 폭, 이미지 세로 대비 높이).
            높이는 줄 간격 여백을 뺀 글자(em 상자) 높이다:
            (줄 수 - 1) × 글자 크기 × 줄 간격 + 글자 크기.
    """
    scale = size * aspect
    if wrap is None:
        widths = [_em(line) * scale for line in text.split("\n")]
    else:
        widths = [
            _em(line) * scale
            for paragraph in text.split("\n")
            for line in _word_wrap(paragraph, wrap / scale)
        ]
    # FE(Konva)에서 줄바꿈 폭(width)을 정한 문구 상자는 줄 길이와 관계없이 그 폭을 차지한다
    width = wrap if wrap is not None else max(widths)
    return width, (len(widths) - 1) * size * _LINE_HEIGHT + size


def _word_wrap(paragraph: str, max_em: float) -> list[str]:
    """FE(Konva wrap="word")처럼 공백에서 줄을 바꾼다. 한 단어가 폭보다 길면 글자에서 바꾼다.

    Args:
        paragraph: 줄바꿈(\\n) 없는 문구.
        max_em: 한 줄 최대 폭 (글자 크기 대비).

    Returns:
        list[str]: 줄 목록.
    """
    lines: list[str] = []
    current = ""
    for word in paragraph.split(" "):
        candidate = f"{current} {word}" if current else word
        if _em(candidate) <= max_em:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = ""
        for char in word:
            if current and _em(current + char) > max_em:
                lines.append(current)
                current = char
            else:
                current += char
    lines.append(current)
    return lines


def _em(text: str) -> float:
    """문구 한 줄의 폭을 글자 크기(em) 대비로 어림한다.

    Returns:
        float: 폭 (em).
    """
    return sum(_char_em(char) for char in text)


def _char_em(char: str) -> float:
    """글자 하나의 폭을 글꼴 크기(em) 대비로 어림한다.

    Returns:
        float: 한글·한자 등 전각 1.0, 공백 0.3, 영문 대문자 0.65, 그 밖의 반각 0.55.
    """
    if char.isspace():
        return 0.3
    if unicodedata.east_asian_width(char) in ("W", "F"):
        return 1.0
    if char.isupper():
        return 0.65
    return 0.55


def _mean_color(
    sample: Image.Image, box: tuple[float, float, float, float]
) -> tuple[float, float, float]:
    """상자 영역의 평균 색을 구한다.

    Returns:
        tuple[float, float, float]: 평균 RGB (0~255).
    """
    left, top, right, bottom = (min(max(value, 0.0), 1.0) for value in box)
    width, height = sample.size
    region = sample.crop(
        (
            int(left * width),
            int(top * height),
            max(int(right * width), int(left * width) + 1),
            max(int(bottom * height), int(top * height) + 1),
        )
    )
    return tuple(ImageStat.Stat(region).mean[:3])


def _contrast_ratio(hex_color: str, rgb: tuple[float, float, float]) -> float:
    """글자색과 배경색의 WCAG 대비비를 구한다.

    Returns:
        float: 1~21. 클수록 읽기 쉽다.
    """
    first = _luminance(_hex_to_rgb(hex_color))
    second = _luminance(rgb)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _contrasting(hex_color: str) -> str:
    """글자색과 대비되는 효과 색(검정 또는 흰색)을 고른다.

    Returns:
        str: 밝은 글자면 "#000000", 어두운 글자면 "#FFFFFF".
    """
    return "#000000" if _luminance(_hex_to_rgb(hex_color)) > 0.4 else "#FFFFFF"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """#RRGGBB를 RGB로 바꾼다.

    Returns:
        tuple[int, int, int]: RGB (0~255).
    """
    return tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))


def _luminance(rgb: tuple[float, float, float]) -> float:
    """WCAG 상대 휘도를 구한다.

    Returns:
        float: 0(검정)~1(흰색).
    """

    def channel(value: float) -> float:
        """sRGB 채널 하나를 선형 값으로 바꾼다."""
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(value) for value in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue
