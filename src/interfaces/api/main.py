"""
FastAPI 메인 애플리케이션
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .metrics import router as metrics_router
from .symbols import router as symbols_router
from .agent import router as agent_router
from src.config.env_config import APP_NAME, APP_VERSION

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="업비트 평가지표 수집 시스템 API",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(metrics_router, prefix="/api/v1", tags=["metrics"])
app.include_router(symbols_router, prefix="/api/v1", tags=["symbols"])
app.include_router(agent_router, prefix="/v1", tags=["agent"])


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health():
    """헬스 체크"""
    return {"status": "healthy"}


