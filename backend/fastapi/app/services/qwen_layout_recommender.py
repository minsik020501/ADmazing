"""Qwen3-VL-4B로 이미지를 보고 문구 배치를 추천하는 추천기.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import logging
import time

from PIL import Image

from app.core.config import settings
from app.schemas.layout_copy import LayoutCopy
from app.services.gpu_out_of_memory_error import GpuOutOfMemoryError
from app.services.layout_prompt import SUBJECT_PROMPT, SYSTEM_PROMPT
from app.utils.device import resolve_device

logger = logging.getLogger(__name__)

# 양자화하지 않을 모듈. 비전 인코더는 작고 양자화 오차에 민감하며,
# lm_head는 출력 토큰 분포에 바로 영향을 주므로 bf16으로 둔다
_MODULES_NOT_TO_QUANTIZE = ["visual", "lm_head"]
# 영역 찾기 출력은 상자 몇 개뿐이라 짧게 둔다
_SUBJECT_MAX_NEW_TOKENS = 160
# 재시도(sample=True)에서 쓰는 샘플링 설정
_SAMPLE_TEMPERATURE = 0.7
_SAMPLE_TOP_P = 0.9


class QwenLayoutRecommender:
    """LAYOUT_MODEL_DIR의 Qwen3-VL을 불러와 압축 추천안 JSON을 생성한다."""

    def __init__(self) -> None:
        """디바이스를 고르고 LAYOUT_QUANT에 맞게 모델을 불러온다.

        int8, int4는 불러오면서 언어 모델 가중치를 torchao로 양자화한다 (cuda 전용).

        Raises:
            FileNotFoundError: 모델 폴더가 없을 때.
            RuntimeError: 요청한 디바이스를 쓸 수 없거나, 양자화를 cuda 밖에서 요청했을 때.
        """
        import torch
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

        self._torch = torch
        self.device = resolve_device(settings.layout_device)
        model_dir = settings.layout_model_dir
        if not model_dir.exists():
            raise FileNotFoundError(
                f"문구 배치 모델 폴더가 없습니다: {model_dir}. "
                "hf download Qwen/Qwen3-VL-4B-Instruct --local-dir "
                "models/qwen3-vl-4b-instruct로 받으세요."
            )

        quant = settings.layout_quant
        if quant != "none" and self.device != "cuda":
            raise RuntimeError(
                f"LAYOUT_QUANT={quant}는 cuda에서만 쓸 수 있습니다 "
                f"(현재 디바이스: {self.device}). 로컬에서는 none을 쓰세요."
            )

        # CPU는 bf16 연산이 느려서 float32로 올린다
        dtype = torch.float32 if self.device == "cpu" else torch.bfloat16
        started = time.perf_counter()
        self.processor = AutoProcessor.from_pretrained(model_dir)
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_dir,
            dtype=dtype,
            quantization_config=_quantization_config(quant),
            # cuda는 GPU로 바로 불러온다. mps는 바로 불러오면 로딩이 멈출 수 있어 나중에 옮긴다
            device_map="cuda" if self.device == "cuda" else None,
        )
        if self.device != "cuda":
            self.model.to(self.device)
        self.model.eval()
        logger.info(
            "문구 배치 모델 로드: %s (device=%s, quant=%s, %.1f초)",
            model_dir,
            self.device,
            quant,
            time.perf_counter() - started,
        )

    def generate(
        self,
        image: Image.Image,
        copies: list[LayoutCopy],
        user_prompt: str,
        sample: bool = False,
    ) -> str:
        """이미지와 지시문을 넣고 압축 추천안 JSON 문자열을 생성한다.

        Args:
            image: 배치를 추천받을 이미지. 긴 변을 LAYOUT_IMAGE_MAX_SIDE로 줄여 넣는다.
            copies: 사용하지 않는다 (문구는 user_prompt에 들어 있다).
            user_prompt: layout_prompt.build_user_prompt로 만든 지시문.
            sample: True면 샘플링, False면 greedy로 생성한다.

        Returns:
            str: 모델 출력 문자열.

        Raises:
            GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
        """
        return self._run(
            image,
            user_prompt,
            SYSTEM_PROMPT,
            settings.layout_max_new_tokens,
            sample,
            "문구 배치 생성",
        )

    def detect_subjects(self, image: Image.Image) -> str:
        """가리면 안 되는 영역(제품, 사람 얼굴)을 찾는다. 출력이 짧아 금방 끝난다.

        Args:
            image: 배치를 추천받을 이미지.

        Returns:
            str: [{"label", "bbox_2d"}] 형태의 JSON 문자열.

        Raises:
            GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
        """
        return self._run(
            image, SUBJECT_PROMPT, None, _SUBJECT_MAX_NEW_TOKENS, False, "영역 찾기"
        )

    def _run(
        self,
        image: Image.Image,
        prompt: str,
        system_prompt: str | None,
        max_new_tokens: int,
        sample: bool,
        name: str,
    ) -> str:
        """이미지와 지시문으로 한 번 생성하고 새로 만든 부분만 문자열로 돌려준다.

        Args:
            image: 입력 이미지. 긴 변을 LAYOUT_IMAGE_MAX_SIDE로 줄여 넣는다.
            prompt: 사용자 지시문.
            system_prompt: 시스템 지시문. 없으면 None.
            max_new_tokens: 최대 출력 토큰 수.
            sample: True면 샘플링, False면 greedy.
            name: 로그에 남길 작업 이름.

        Returns:
            str: 모델 출력 문자열.

        Raises:
            GpuOutOfMemoryError: 생성 중 GPU 메모리가 부족할 때.
        """
        resized = image.convert("RGB")
        resized.thumbnail(
            (settings.layout_image_max_side, settings.layout_image_max_side)
        )
        messages = []
        if system_prompt:
            messages.append(
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]}
            )
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": resized},
                    {"type": "text", "text": prompt},
                ],
            }
        )
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)

        options = {"max_new_tokens": max_new_tokens, "do_sample": sample}
        if sample:
            options.update(temperature=_SAMPLE_TEMPERATURE, top_p=_SAMPLE_TOP_P)
        else:
            # 모델 기본 generation_config의 샘플링 값이 greedy 경고를 내지 않게 비운다
            options.update(temperature=None, top_p=None, top_k=None)

        started = time.perf_counter()
        try:
            with self._torch.inference_mode():
                output_ids = self.model.generate(**inputs, **options)
        except self._torch.cuda.OutOfMemoryError as error:
            self._torch.cuda.empty_cache()
            raise GpuOutOfMemoryError from error

        prompt_length = inputs["input_ids"].shape[1]
        generated = output_ids[0, prompt_length:]
        logger.info(
            "%s: 입력 %d 토큰, 출력 %d 토큰, %.1f초 (sample=%s)",
            name,
            prompt_length,
            generated.shape[0],
            time.perf_counter() - started,
            sample,
        )
        return self.processor.decode(generated, skip_special_tokens=True)


def _quantization_config(quant: str):
    """LAYOUT_QUANT에 맞는 torchao 양자화 설정을 만든다.

    Args:
        quant: none, int8, int4.

    Returns:
        TorchAoConfig | None: 양자화 설정. none이면 None.
    """
    if quant == "none":
        return None
    from torchao.quantization import Int4WeightOnlyConfig, Int8WeightOnlyConfig
    from transformers import TorchAoConfig

    quant_type = (
        Int8WeightOnlyConfig()
        if quant == "int8"
        else Int4WeightOnlyConfig(group_size=128)
    )
    return TorchAoConfig(
        quant_type=quant_type, modules_to_not_convert=_MODULES_NOT_TO_QUANTIZE
    )
