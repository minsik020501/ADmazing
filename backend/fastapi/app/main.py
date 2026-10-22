"""FastAPI 애플리케이션 진입점.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-22
수정자: ven_choi
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import generate, health
from app.core.config import settings
from app.services.image_generator_factory import create_image_generator
from app.utils.validation_message import to_korean_errors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 이미지 생성기를 한 번만 로드한다.

    Args:
        app: FastAPI 애플리케이션 인스턴스.

    Yields:
        None: 서버가 실행되는 동안 제어를 넘긴다.
    """
    app.state.image_generator = create_image_generator()
    yield


app = FastAPI(title="Admazing API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """요청 검증 에러(422)의 메시지를 한국어로 바꿔 응답한다.

    응답 구조는 FastAPI 기본 422 응답(detail: [{loc, msg, type, ...}])과 같다.

    Args:
        request: 요청 객체.
        exc: 요청 검증 에러.

    Returns:
        JSONResponse: msg를 한국어로 바꾼 422 응답.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(to_korean_errors(exc.errors()))},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
