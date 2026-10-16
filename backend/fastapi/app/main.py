"""FastAPI 애플리케이션 진입점.

생성일자: 2026-10-16
생성자: ven_choi
수정일자: 2026-10-16
수정자: ven_choi
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import generate, health
from app.core.config import settings
from app.services.image_generator_factory import create_image_generator


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
