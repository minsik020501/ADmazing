"""GPU를 쓰는 작업이 함께 쓰는 잠금. 지금은 이미지 생성만 GPU를 쓴다.

GPU 작업이 늘어나도 메모리 피크가 겹치지 않도록 한 번에 하나씩 실행한다.
(문구 배치 추천은 템플릿·CPU 검출기로 바뀌어 GPU를 쓰지 않는다)

생성일자: 2026-11-06
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

import threading

gpu_lock = threading.Lock()
