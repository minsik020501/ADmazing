"""문구 상자 크기를 글자 수로 어림하는 유틸리티.

서버에는 글꼴 파일이 없어 실제로 그려 재지 못한다. 글자 종류별 폭(em)으로 어림하고,
줄바꿈은 FE(Konva wrap="word")처럼 공백에서 한다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import unicodedata
from typing import Literal

# (왼쪽, 위, 오른쪽, 아래) 이미지 대비 비율
Box = tuple[float, float, float, float]


def box_size(
    text: str,
    size: float,
    aspect: float,
    wrap: float | None = None,
    line_height: float = 1.2,
) -> tuple[float, float]:
    """문구 상자 크기를 어림한다.

    Args:
        text: 문구 (줄바꿈 \\n 포함 가능).
        size: 글자 크기 (이미지 세로 대비).
        aspect: 이미지 세로 / 가로.
        wrap: 줄바꿈 폭 (이미지 가로 대비). None이면 \\n에서만 줄을 바꾼다.
        line_height: 줄 간격 (글자 크기 대비).

    Returns:
        tuple[float, float]: (이미지 가로 대비 폭, 이미지 세로 대비 높이).
            FE에서 width를 정한 상자는 그 폭을 차지하므로 wrap이 있으면 폭은 wrap이다.
            높이는 줄 간격 여백을 뺀 글자(em 상자) 높이다.
    """
    lines = line_count(text, size, aspect, wrap)
    if wrap is not None:
        width = wrap
    else:
        width = max(em_width(line) for line in text.split("\n")) * size * aspect
    return width, (lines - 1) * size * line_height + size


def line_count(text: str, size: float, aspect: float, wrap: float | None) -> int:
    """줄바꿈 후 줄 수를 어림한다.

    Returns:
        int: 줄 수.
    """
    return len(wrap_lines(text, size, aspect, wrap))


def wrap_lines(text: str, size: float, aspect: float, wrap: float | None) -> list[str]:
    """줄바꿈한 줄 목록을 어림한다.

    Args:
        text: 문구 (줄바꿈 \\n 포함 가능).
        size: 글자 크기 (이미지 세로 대비).
        aspect: 이미지 세로 / 가로.
        wrap: 줄바꿈 폭 (이미지 가로 대비). None이면 \\n에서만 줄을 바꾼다.

    Returns:
        list[str]: 줄 목록.
    """
    paragraphs = text.split("\n")
    if wrap is None:
        return paragraphs
    max_em = wrap / (size * aspect)
    return [line for paragraph in paragraphs for line in word_wrap(paragraph, max_em)]


def line_boxes(
    text: str,
    size: float,
    aspect: float,
    wrap: float | None,
    line_height: float,
    align: Literal["left", "center", "right"],
    center: tuple[float, float],
) -> list[Box]:
    """줄마다 글자가 차지하는 영역을 어림한다.

    상자 전체(box_size)는 줄바꿈 폭을 다 차지하지만, 짧은 줄은 그 일부에만 글자가 있다.
    글자 아래 배경만 보려고 줄별 영역을 따로 구한다. 줄은 FE(Konva)처럼 상자 위에서부터
    글자 크기 × line_height 간격으로 놓고, 상자 안에서 align대로 정렬한다.

    Args:
        text: 문구.
        size: 글자 크기 (이미지 세로 대비).
        aspect: 이미지 세로 / 가로.
        wrap: 줄바꿈 폭 (이미지 가로 대비).
        line_height: 줄 간격 (글자 크기 대비).
        align: 상자 안 줄 정렬.
        center: 상자 가운데 (x, y) 비율.

    Returns:
        list[Box]: 줄별 영역 (빈 줄은 뺀다).
    """
    box_w, box_h = box_size(text, size, aspect, wrap, line_height)
    left, top = center[0] - box_w / 2, center[1] - box_h / 2
    boxes = []
    for index, line in enumerate(wrap_lines(text, size, aspect, wrap)):
        width = min(em_width(line) * size * aspect, box_w)
        if width <= 0:
            continue
        if align == "left":
            x = left
        elif align == "right":
            x = left + box_w - width
        else:
            x = center[0] - width / 2
        y = top + index * size * line_height
        boxes.append((x, y, x + width, y + size))
    return boxes


def word_wrap(paragraph: str, max_em: float) -> list[str]:
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
        if em_width(candidate) <= max_em:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = ""
        for char in word:
            if current and em_width(current + char) > max_em:
                lines.append(current)
                current = char
            else:
                current += char
    lines.append(current)
    return lines


def em_width(text: str) -> float:
    """문구 한 줄의 폭을 글자 크기(em) 대비로 어림한다.

    Returns:
        float: 폭 (em). 한글·한자 등 전각 1.0, 공백 0.3, 영문 대문자 0.65, 그 밖의 반각 0.55.
    """
    total = 0.0
    for char in text:
        if char.isspace():
            total += 0.3
        elif unicodedata.east_asian_width(char) in ("W", "F"):
            total += 1.0
        elif char.isupper():
            total += 0.65
        else:
            total += 0.55
    return total
