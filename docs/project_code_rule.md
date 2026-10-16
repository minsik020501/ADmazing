# Project code rule

코드 설계에 대한 규칙을 다음과 같이 정의합니다.

1. 모든 메서드는 아래 형식의 주석을 사용합니다.
    - Backend(Python): Google style docstring (`Args:`, `Returns:`, `Raises:`)
    - Frontend(TS/TSX): JSDoc (`@param`, `@returns`, `@throws`)
2. 간단한 메서드의 경우 parameter를 정의하지 않습니다.
3. 모든 메서드는 return 값이 있을 경우 무엇인지 적어야 합니다.
4. 파일에는 클래스가 하나만 존재해야하며, 모든 파일에는 생성일자, 생성자, 수정일자, 수정자를 포함해야 합니다.
    - 파일을 수정한 경우 수정일자와 수정자를 갱신합니다.
5. Python의 경우 Black으로, Frontend의 경우 Prettier로 포맷팅을 지정하고, 커밋 전 반드시 포맷팅을 적용합니다.
    - Backend: `pip install -r backend/requirements-dev.txt` 후 `black backend` (설정: `backend/pyproject.toml`, line-length 88)
    - Frontend: `cd frontend && npm run format` (설정: `frontend/.prettierrc.json`, printWidth 100)
