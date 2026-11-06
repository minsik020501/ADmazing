"""문구로 가리면 안 되는 영역(제품, 사람 얼굴)을 찾는 검출기.

CPU에서 onnxruntime·OpenCV로 돈다 (GPU를 쓰지 않아 이미지 생성과 기다리지 않는다).
    - 주 피사체: U²-Net (배경 제거용 주 피사체 분리). 마스크의 가장 큰 덩어리를 제품으로 본다
    - 얼굴: OpenCV YuNet

보완 규칙:
    - 이미지의 2%보다 작은 피사체는 잡음으로 보고 뺀다 (장면 사진의 의자, 테이블 다리 등)
    - 가장 큰 얼굴의 30%보다 작은 얼굴은 배경 인물로 보고 뺀다
    - 클로즈업(피사체가 이미지의 45%를 넘고 얼굴을 품음)이면 사람 전체 대신 얼굴과 그 주변
      (손에 든 제품 자리)만 피한다. 전신 사진(패션 등)은 사람 전체를 피한다

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

Box = tuple[float, float, float, float]

# U²-Net 입력 크기와 정규화 값 (rembg와 같다)
_SALIENT_SIZE = 320
_MEAN = (0.485, 0.456, 0.406)
_STD = (0.229, 0.224, 0.225)
# 얼굴 검출에 넣을 이미지 긴 변과 최소 점수
_FACE_SIDE = 640
_FACE_SCORE = 0.7

# 보완 규칙 값
MIN_PRODUCT_AREA = 0.02
MIN_FACE_AREA_RATIO = 0.3
CLOSE_UP_AREA = 0.45
# 클로즈업에서 피할 영역: 얼굴 상자를 옆으로 얼굴 폭의 몇 배, 아래로 얼굴 높이의 몇 배 넓힌다
CLOSE_UP_SIDE = 0.5
CLOSE_UP_BELOW = 0.5


class SubjectDetector:
    """주 피사체(U²-Net)와 얼굴(YuNet)로 가리면 안 되는 영역을 찾는다."""

    def __init__(self, salient_model: Path, face_model: Path) -> None:
        """두 모델을 불러온다.

        Args:
            salient_model: U²-Net ONNX 파일 (u2net.onnx).
            face_model: YuNet ONNX 파일 (face_detection_yunet_2023mar.onnx).

        Raises:
            FileNotFoundError: 모델 파일이 없을 때.
        """
        import cv2
        import onnxruntime

        for path in (salient_model, face_model):
            if not path.exists():
                raise FileNotFoundError(
                    f"영역 찾기 모델이 없습니다: {path}. "
                    ".env.example의 LAYOUT_SALIENT_MODEL_PATH 설명대로 받으세요."
                )
        self._cv2 = cv2
        self._salient = onnxruntime.InferenceSession(
            str(salient_model), providers=["CPUExecutionProvider"]
        )
        self._salient_input = self._salient.get_inputs()[0].name
        self._face = cv2.FaceDetectorYN.create(
            str(face_model), "", (320, 320), _FACE_SCORE
        )

    def detect(self, image: Image.Image) -> list[tuple[str, Box]]:
        """가리면 안 되는 영역 목록을 찾는다.

        Args:
            image: 원본 이미지.

        Returns:
            list[tuple[str, Box]]: [("product" | "face", (왼쪽, 위, 오른쪽, 아래) 비율)].
                찾은 것이 없으면 빈 목록 (장면 사진 등).
        """
        rgb = image.convert("RGB")
        product = self._salient_box(rgb)
        faces = self._faces(rgb)
        if faces:
            largest = max(_area(face) for face in faces)
            faces = [f for f in faces if _area(f) >= largest * MIN_FACE_AREA_RATIO]

        if product is not None and faces:
            main_face = max(faces, key=_area)
            if _area(product) > CLOSE_UP_AREA and _contains_center(product, main_face):
                product = _close_up_zone(main_face, product)

        subjects = [("face", face) for face in faces]
        if product is not None:
            subjects.insert(0, ("product", product))
        return subjects

    def _salient_box(self, image: Image.Image) -> Box | None:
        """U²-Net 마스크에서 가장 큰 덩어리의 상자를 구한다.

        Returns:
            Box | None: 상자. 없거나 MIN_PRODUCT_AREA보다 작으면 None.
        """
        import numpy as np

        resized = image.resize((_SALIENT_SIZE, _SALIENT_SIZE), Image.Resampling.LANCZOS)
        pixels = np.asarray(resized, dtype=np.float32)
        pixels = pixels / max(float(pixels.max()), 1e-6)
        pixels = (pixels - np.array(_MEAN, dtype=np.float32)) / np.array(
            _STD, dtype=np.float32
        )
        batch = pixels.transpose(2, 0, 1)[None].astype(np.float32)
        prediction = self._salient.run(None, {self._salient_input: batch})[0][0, 0]
        low, high = float(prediction.min()), float(prediction.max())
        mask = ((prediction - low) / max(high - low, 1e-6)) > 0.5

        count, _, stats, _ = self._cv2.connectedComponentsWithStats(
            mask.astype(np.uint8)
        )
        if count <= 1:
            return None
        largest = 1 + int(np.argmax(stats[1:, self._cv2.CC_STAT_AREA]))
        x, y, w, h, _ = (int(v) for v in stats[largest])
        box = (
            x / _SALIENT_SIZE,
            y / _SALIENT_SIZE,
            (x + w) / _SALIENT_SIZE,
            (y + h) / _SALIENT_SIZE,
        )
        return box if _area(box) >= MIN_PRODUCT_AREA else None

    def _faces(self, image: Image.Image) -> list[Box]:
        """얼굴 상자들을 찾는다.

        Returns:
            list[Box]: 상자 목록.
        """
        import numpy as np

        small = image.copy()
        small.thumbnail((_FACE_SIDE, _FACE_SIDE))
        frame = self._cv2.cvtColor(np.asarray(small), self._cv2.COLOR_RGB2BGR)
        height, width = frame.shape[:2]
        self._face.setInputSize((width, height))
        _, faces = self._face.detect(frame)
        boxes = []
        for face in faces if faces is not None else []:
            x, y, w, h = (float(v) for v in face[:4])
            boxes.append(
                (
                    max(x / width, 0.0),
                    max(y / height, 0.0),
                    min((x + w) / width, 1.0),
                    min((y + h) / height, 1.0),
                )
            )
        return boxes


def union_box(boxes: list[Box]) -> Box | None:
    """상자들을 모두 감싸는 상자를 구한다.

    Returns:
        Box | None: 감싸는 상자. 상자가 없으면 None.
    """
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _close_up_zone(face: Box, person: Box) -> Box:
    """클로즈업에서 피할 영역: 얼굴과 그 옆·아래(손에 든 제품 자리)를 사람 상자 안으로.

    Returns:
        Box: 영역.
    """
    face_w, face_h = face[2] - face[0], face[3] - face[1]
    return (
        max(face[0] - face_w * CLOSE_UP_SIDE, person[0]),
        max(face[1], person[1]),
        min(face[2] + face_w * CLOSE_UP_SIDE, person[2]),
        min(face[3] + face_h * CLOSE_UP_BELOW, person[3]),
    )


def _contains_center(outer: Box, inner: Box) -> bool:
    """inner 상자의 가운데가 outer 안에 있는지 확인한다.

    Returns:
        bool: 안에 있으면 True.
    """
    cx, cy = (inner[0] + inner[2]) / 2, (inner[1] + inner[3]) / 2
    return outer[0] <= cx <= outer[2] and outer[1] <= cy <= outer[3]


def _area(box: Box) -> float:
    """상자 넓이.

    Returns:
        float: 넓이 (비율²).
    """
    return max(box[2] - box[0], 0) * max(box[3] - box[1], 0)
