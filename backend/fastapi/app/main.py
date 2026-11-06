"""FastAPI 애플리케이션 진입점.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-11-06
수정자: ven_choi
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import copy_recommend, generate, health, jobs, layout_recommend
from app.core.config import settings
from app.services.copy_recommender_factory import create_copy_recommender
from app.services.generation_job_store import GenerationJobStore
from app.services.image_generator_factory import create_image_generator
from app.services.layout_recommender_factory import create_layout_recommender
from app.utils.validation_message import to_korean_errors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 이미지 생성기와 문구 배치 모델을 한 번만 로드하고
    문구 추천기와 작업 저장소를 만든다.

    Args:
        app: FastAPI 애플리케이션 인스턴스.

    Yields:
        None: 서버가 실행되는 동안 제어를 넘긴다.
    """
    app.state.image_generator = create_image_generator()
    app.state.copy_recommender = create_copy_recommender()
    app.state.layout_recommender = create_layout_recommender()
    app.state.job_store = GenerationJobStore()
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
app.include_router(jobs.router, prefix="/api")
app.include_router(copy_recommend.router, prefix="/api")
app.include_router(layout_recommend.router, prefix="/api")
