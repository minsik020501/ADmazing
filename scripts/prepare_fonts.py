"""fonts/manifest.json의 광고용 폰트를 받아 웹폰트로 준비하고 @font-face CSS를 만든다.

- 원본은 FONT_SOURCE_DIR(기본 fonts/src/<id>/)에 받아 둔다. 받은 파일은 다시 받지 않는다
- 직접 받아야 하는 폰트(manual)는 fonts/manual/<id>/에 넣어 둔다
- 결과는 FONT_OUTPUT_DIR(기본 frontend/public/fonts/)/<id>/<id>-<굵기>.<형식>에 저장한다
  - allow_convert가 true면 woff2로 변환한다 (글자를 빼는 서브셋 없이 형식만 바꿈)
  - false(수정 금지 라이선스)면 배포처 파일을 그대로 복사한다
  - 가변 폰트(variable)는 지정한 굵기마다 고정 굵기로 만든 뒤 woff2로 저장한다
- frontend/src/styles/fonts.css는 manifest만 보고 만든다 (받은 파일과 상관없이 항상 같은 결과).
  내용이 바뀔 때만 다시 쓰므로, manifest를 고친 뒤 로컬에서 실행해 커밋한다

docker compose에서는 font-prep 서비스가 --no-css --keep-going으로 실행해 볼륨에 준비한다.

실행 (레포 루트에서):
    pip install -r scripts/requirements.txt
    python scripts/prepare_fonts.py            # 없는 것만 준비 + CSS 갱신
    python scripts/prepare_fonts.py --force    # 결과를 모두 다시 만듦

생성일자: 2026-11-04
생성자: ven_choi
수정일자: 2026-11-04
수정자: ven_choi
"""

import argparse
import json
import os
import re
import shutil
import sys
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "fonts" / "manifest.json"
MANUAL_DIR = ROOT / "fonts" / "manual"
SOURCE_DIR = Path(os.environ.get("FONT_SOURCE_DIR", ROOT / "fonts" / "src"))
OUTPUT_DIR = Path(
    os.environ.get("FONT_OUTPUT_DIR", ROOT / "frontend" / "public" / "fonts")
)
CSS_PATH = ROOT / "frontend" / "src" / "styles" / "fonts.css"
# 브라우저에서 읽는 경로 (Vite는 public/을 루트로 제공)
PUBLIC_URL = "/fonts"

CSS_FORMATS = {
    ".woff2": "woff2",
    ".woff": "woff",
    ".ttf": "truetype",
    ".otf": "opentype",
}
USER_AGENT = "admazing-font-prep"
# frontend/.prettierrc.json의 printWidth
PRETTIER_WIDTH = 100


def parse_args() -> argparse.Namespace:
    """커맨드라인 인자를 파싱한다.

    Returns:
        argparse.Namespace: 실행 옵션.
    """
    parser = argparse.ArgumentParser(description="광고용 웹폰트 준비")
    parser.add_argument("--force", action="store_true", help="결과를 모두 다시 만든다")
    parser.add_argument("--only", nargs="+", help="준비할 폰트 id (기본: 전체)")
    parser.add_argument(
        "--no-css", action="store_true", help="fonts.css를 갱신하지 않는다"
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="받기·변환에 실패한 폰트가 있어도 종료 코드 0으로 끝낸다",
    )
    return parser.parse_args()


def main() -> int:
    """manifest의 폰트를 준비하고 CSS를 만든다.

    Returns:
        int: 종료 코드 (0: 성공, 1: 실패한 폰트가 있음).
    """
    args = parse_args()
    fonts = json.loads(MANIFEST.read_text())["fonts"]
    targets = [font for font in fonts if not args.only or font["id"] in args.only]

    failed, missing = [], []
    for font in targets:
        try:
            if not prepare_font(font, args.force):
                missing.append(font)
        except Exception as error:  # 한 폰트가 실패해도 나머지는 계속 준비한다
            print(f"[실패] {font['id']}: {error}", file=sys.stderr)
            failed.append(font["id"])

    if not args.no_css:
        write_css(fonts)
    print_summary(fonts)

    for font in missing:
        print(
            f"[직접 받기 필요] {font['name']}: {font['manual']['download_page']}\n"
            f"    → fonts/manual/{font['id']}/ 에 "
            + ", ".join(file["filename"] for file in font["files"])
            + " 로 넣고 다시 실행하세요"
        )
    if failed:
        print(f"실패: {', '.join(failed)}", file=sys.stderr)
        if not args.keep_going:
            return 1
    return 0


def output_files(font: dict) -> list[tuple[int, Path]]:
    """manifest만 보고 폰트의 결과 파일 경로를 정한다.

    Args:
        font: manifest의 폰트 항목.

    Returns:
        list[tuple[int, Path]]: (굵기, OUTPUT_DIR 기준 상대 경로) 목록.
    """
    if "variable" in font:
        return [
            (weight, Path(font["id"]) / f"{font['id']}-{weight}.woff2")
            for weight in font["variable"]["weights"]
        ]

    outputs = []
    for file in font["files"]:
        name = file.get("filename") or Path(urlsplit(file["url"]).path).name
        suffix = ".woff2" if font["allow_convert"] else Path(name).suffix
        outputs.append(
            (
                file["weight"],
                Path(font["id"]) / f"{font['id']}-{file['weight']}{suffix}",
            )
        )
    return outputs


def prepare_font(font: dict, force: bool) -> bool:
    """폰트 하나의 굵기별 웹폰트 파일을 만든다.

    Args:
        font: manifest의 폰트 항목.
        force: 이미 있는 결과도 다시 만들지 여부.

    Returns:
        bool: 준비했으면 True, 직접 받아야 하는 원본이 없어 건너뛰었으면 False.
    """
    (OUTPUT_DIR / font["id"]).mkdir(parents=True, exist_ok=True)

    if "variable" in font:
        source = download(font["id"], font["variable"]["url"])
        for weight, relative in output_files(font):
            output = OUTPUT_DIR / relative
            if force or not output.exists():
                instantiate_to_woff2(source, weight, output)
                print(f"[가변→고정] {relative}")
        return True

    for file, (_, relative) in zip(font["files"], output_files(font)):
        output = OUTPUT_DIR / relative
        if not force and output.exists():
            continue
        if "url" in file:
            source = download(font["id"], file["url"])
        else:
            source = MANUAL_DIR / font["id"] / file["filename"]
            if not source.exists():
                return False

        if output.suffix == ".woff2" and source.suffix != ".woff2":
            to_woff2(source, output)
            print(f"[변환] {relative}")
        else:
            shutil.copy2(source, output)
            print(f"[복사] {relative}")
    return True


def download(font_id: str, url: str) -> Path:
    """원본 파일을 SOURCE_DIR/<id>/에 받는다. 이미 있으면 받지 않는다.

    Args:
        font_id: 폰트 id (저장 폴더 이름).
        url: 원본 주소. 공백·한글·대괄호가 있어도 된다.

    Returns:
        Path: 받은 파일 경로.
    """
    parts = urlsplit(url)
    target = SOURCE_DIR / font_id / Path(parts.path).name
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = urlunsplit(parts._replace(path=quote(parts.path, safe="/@%")))
    request = urllib.request.Request(encoded, headers={"User-Agent": USER_AGENT})
    print(f"[받기] {url}", flush=True)
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    # 중간에 끊겨 깨진 파일이 남지 않도록 다 받은 뒤에 저장한다
    temp = target.with_name(target.name + ".part")
    temp.write_bytes(data)
    temp.rename(target)
    return target


def to_woff2(source: Path, output: Path) -> None:
    """ttf·otf·woff를 글리프 변경 없이 woff2로 저장한다."""
    from fontTools.ttLib import TTFont

    font = TTFont(source)
    font.flavor = "woff2"
    font.save(output)


def instantiate_to_woff2(source: Path, weight: int, output: Path) -> None:
    """가변 폰트를 지정한 굵기의 고정 폰트로 만들어 woff2로 저장한다."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    font = instantiateVariableFont(TTFont(source), {"wght": weight})
    font.flavor = "woff2"
    font.save(output)


def write_css(fonts: list[dict]) -> None:
    """manifest로 @font-face CSS를 만든다. 내용이 같으면 파일을 건드리지 않는다."""
    body = []
    for font in fonts:
        body.append("")
        body.append(f"/* {font['name']} — {font['license']} */")
        for weight, relative in output_files(font):
            url = f'url("{PUBLIC_URL}/{relative.as_posix()}")'
            css_format = f'format("{CSS_FORMATS[relative.suffix]}");'
            src = f"  src: {url} {css_format}"
            # Prettier(printWidth 100)와 같은 결과가 되도록 긴 줄은 format을 다음 줄로 넘긴다
            if len(src) > PRETTIER_WIDTH:
                src = f"  src: {url}\n    {css_format}"
            body += [
                "@font-face {",
                f'  font-family: "{font["family"]}";',
                src,
                f"  font-weight: {weight};",
                "  font-style: normal;",
                "  font-display: swap;",
                "}",
            ]
    body_text = "\n".join(body) + "\n"

    today = date.today().isoformat()
    created = today
    if CSS_PATH.exists():
        current = CSS_PATH.read_text()
        if current.endswith(body_text):
            print("[CSS] 변경 없음")
            return
        found = re.search(r"생성일자: (\S+)", current)
        created = found.group(1) if found else today

    header = "\n".join(
        [
            "/**",
            " * 광고 문구용 웹폰트 (@font-face).",
            " * scripts/prepare_fonts.py가 fonts/manifest.json으로 만든 파일이다. 직접 수정하지 않는다.",
            " * 폰트 파일은 docker compose의 font-prep이 준비하며, 실제로 쓰일 때만 내려받는다.",
            " *",
            f" * 생성일자: {created}",
            " * 생성자: ven_choi",
            f" * 수정일자: {today}",
            " * 수정자: ven_choi",
            " */",
        ]
    )
    CSS_PATH.write_text(header + "\n" + body_text)
    print(f"[CSS] {CSS_PATH.relative_to(ROOT)}")


def print_summary(fonts: list[dict]) -> None:
    """폰트별 준비된 굵기와 크기를 출력한다."""
    total = 0
    for font in fonts:
        ready = [
            (weight, OUTPUT_DIR / relative)
            for weight, relative in output_files(font)
            if (OUTPUT_DIR / relative).exists()
        ]
        size = sum(path.stat().st_size for _, path in ready)
        total += size
        weights = ", ".join(str(weight) for weight, _ in ready) or "없음"
        print(f"  {font['id']:<30} {weights:<15} {size / 1024**2:6.2f}MB")
    print(f"  {'합계':<30} {'':<15} {total / 1024**2:6.2f}MB")


if __name__ == "__main__":
    sys.exit(main())
