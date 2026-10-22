"""요청 검증(422) 에러 메시지를 한국어로 바꾸는 유틸리티.

생성일자: 2026-10-22
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

# pydantic 에러 type → 한국어 메시지. {field}와 ctx 값(le, ge 등)을 채워 넣는다
_FIELD_MESSAGES = {
    "missing": "'{field}' 값은 필수입니다.",
    "less_than_equal": "'{field}' 값은 {le} 이하여야 합니다.",
    "greater_than_equal": "'{field}' 값은 {ge} 이상이어야 합니다.",
    "multiple_of": "'{field}' 값은 {multiple_of}의 배수여야 합니다.",
    "string_too_short": "'{field}' 값은 최소 {min_length}자 이상이어야 합니다.",
    "string_type": "'{field}' 값은 문자열이어야 합니다.",
    "int_type": "'{field}' 값은 정수여야 합니다.",
    "int_parsing": "'{field}' 값은 정수여야 합니다.",
    "int_from_float": "'{field}' 값은 정수여야 합니다.",
}

# 필드가 아닌 요청 본문 전체에 대한 에러
_BODY_MESSAGES = {
    "json_invalid": "요청 본문이 올바른 JSON 형식이 아닙니다.",
    "missing": "요청 본문이 필요합니다.",
    "model_attributes_type": "요청 본문은 JSON 객체여야 합니다.",
}


def to_korean_errors(errors: list[dict]) -> list[dict]:
    """pydantic 검증 에러 목록의 msg를 한국어로 바꾼다.

    번역할 수 없는 type은 원래 메시지를 그대로 둔다.

    Args:
        errors: RequestValidationError.errors()가 반환한 에러 목록.

    Returns:
        list[dict]: msg만 한국어로 바꾼 에러 목록.
    """
    translated = []
    for error in errors:
        loc = error.get("loc", ())
        # loc는 ("body", "seed")처럼 위치 다음에 필드 이름이 온다.
        # JSON 파싱 에러는 ("body", 1)처럼 필드 이름 대신 오류 위치(숫자)가 온다
        field = loc[-1] if len(loc) > 1 and isinstance(loc[-1], str) else None
        if field is None:
            template = _BODY_MESSAGES.get(error["type"])
        else:
            template = _FIELD_MESSAGES.get(error["type"])

        message = error["msg"]
        if template is not None:
            try:
                message = template.format(field=field, **error.get("ctx", {}))
            except KeyError:
                pass
        translated.append({**error, "msg": message})
    return translated
