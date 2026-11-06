"""GPU를 쓰는 작업(이미지 생성, 문구 배치 추천)이 함께 쓰는 잠금.

두 모델이 같은 GPU에 올라가므로 메모리 피크가 겹치지 않도록 한 번에 하나씩 실행한다.

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import threading

gpu_lock = threading.Lock()
