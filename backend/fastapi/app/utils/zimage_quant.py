"""Z-Image 양자화 모델 폴더와 양자화 설정을 다루는 유틸리티.

변환(app/cli/prepare_zimage.py)과 서버 로더(zimage_image_generator.py)가 같은 폴더
규칙과 버전 확인을 쓰도록 한곳에 모은다.

생성일자: 2026-11-04
생성자: ven_choi
수정일자: 2026-11-04
수정자: ven_choi
"""

import json
from importlib import metadata
from pathlib import Path

# 변환이 끝까지 성공했을 때만 쓰는 표시 파일. 없으면 변환이 안 됐거나 중간에 멈춘 것이다
INFO_FILE = "quant_info.json"

# 저장된 양자화 가중치는 이 패키지들의 버전에 묶이므로, 버전이 바뀌면 다시 변환한다
VERSIONED_PACKAGES = ("torch", "torchao", "diffusers", "transformers")

# fp8 가중치(float8_e4m3fn)를 다루려면 SM 8.9 이상(Ada, Hopper 이후)이 필요하다. L4는 8.9
FP8_MIN_CAPABILITY = (8, 9)


def quant_model_dir(model_dir: Path, quant: str) -> Path:
    """원본 모델 폴더 옆에 둘 양자화 모델 폴더 경로를 만든다.

    Args:
        model_dir: 원본(bf16) Z-Image 모델 폴더.
        quant: int8 또는 fp8.

    Returns:
        Path: 예) /models/z-image-turbo → /models/z-image-turbo-fp8
    """
    return model_dir.with_name(f"{model_dir.name}-{quant}")


def package_versions() -> dict[str, str | None]:
    """양자화 가중치 호환성에 영향을 주는 패키지 버전을 모은다.

    Returns:
        dict[str, str | None]: 패키지 이름 → 버전 (설치되지 않았으면 None).
    """
    versions = {}
    for package in VERSIONED_PACKAGES:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def read_info(quant_dir: Path) -> dict | None:
    """양자화 모델 폴더의 표시 파일을 읽는다.

    Returns:
        dict | None: 표시 파일 내용. 파일이 없거나 깨졌으면 None.
    """
    try:
        return json.loads((quant_dir / INFO_FILE).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def stale_reason(quant_dir: Path, quant: str) -> str | None:
    """양자화 모델 폴더를 그대로 쓸 수 없는 이유를 찾는다.

    Args:
        quant_dir: 양자화 모델 폴더.
        quant: 기대하는 양자화 종류 (int8, fp8).

    Returns:
        str | None: 다시 변환해야 하는 이유. 그대로 쓸 수 있으면 None.
    """
    info = read_info(quant_dir)
    if info is None:
        return f"{quant_dir}에 변환 완료 표시({INFO_FILE})가 없습니다"
    if info.get("quant") != quant:
        return f"양자화 종류가 다릅니다 (저장됨: {info.get('quant')}, 설정: {quant})"
    saved, current = info.get("packages", {}), package_versions()
    changed = [
        f"{name} {saved.get(name)} → {current[name]}"
        for name in VERSIONED_PACKAGES
        if saved.get(name) != current[name]
    ]
    if changed:
        return "패키지 버전이 바뀌었습니다: " + ", ".join(changed)
    return None


def check_cuda(torch, quant: str) -> None:
    """양자화 모델을 쓸 수 있는 GPU인지 확인한다.

    Args:
        torch: torch 모듈.
        quant: int8 또는 fp8.

    Raises:
        RuntimeError: CUDA를 쓸 수 없거나, fp8을 지원하지 않는 GPU일 때.
    """
    if not torch.cuda.is_available():
        raise RuntimeError(
            f"ZIMAGE_QUANT={quant}는 CUDA GPU에서만 쓸 수 있습니다. "
            "GPU 설정(docker-compose.gpu.yml)이 포함됐는지 확인하세요."
        )
    if quant == "fp8":
        capability = torch.cuda.get_device_capability()
        if capability < FP8_MIN_CAPABILITY:
            raise RuntimeError(
                f"{torch.cuda.get_device_name()}(SM {capability[0]}.{capability[1]})는 "
                "fp8을 지원하지 않습니다 (SM 8.9 이상 필요). ZIMAGE_QUANT=int8을 쓰세요."
            )


def torchao_quant_type(quant: str):
    """양자화 종류에 맞는 torchao 설정을 만든다.

    둘 다 weight-only라 연산은 bf16으로 하고, 가중치만 8bit로 저장해 메모리를 절반으로 줄인다.

    Args:
        quant: int8 또는 fp8.

    Returns:
        AOBaseConfig: torchao 양자화 설정.

    Raises:
        ValueError: 지원하지 않는 양자화 종류일 때.
    """
    from torchao.quantization import Float8WeightOnlyConfig, Int8WeightOnlyConfig

    if quant == "fp8":
        return Float8WeightOnlyConfig()
    if quant == "int8":
        return Int8WeightOnlyConfig()
    raise ValueError(f"지원하지 않는 양자화 종류입니다: {quant}")
