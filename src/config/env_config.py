"""
환경 변수 설정
.env 파일이 있으면 우선 사용, 없으면 기본값 사용
"""
import os
from pathlib import Path
from typing import Optional

# .env 파일 경로
ENV_FILE = Path(__file__).parent.parent.parent / ".env"

# .env 파일이 있으면 로드
if ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        pass  # python-dotenv가 없어도 동작

# 업비트 API 설정
UPBIT_ACCESS_KEY: str = os.getenv("UPBIT_ACCESS_KEY", "8fngRxfhmRqRPlFIjAXz518SjXeUEYzv6lLJIZOg")
UPBIT_SECRET_KEY: str = os.getenv("UPBIT_SECRET_KEY", "CRLmPYOUmkPRGbwu4oERLuvxQARZyPbDHP60tSdl")

# 데이터베이스 설정
# DATABASE_URL이 직접 제공되면 사용, 없으면 POSTGRES_USER/PASSWORD로 구성
if os.getenv("DATABASE_URL"):
    DATABASE_URL: str = os.getenv("DATABASE_URL")
else:
    # POSTGRES_USER와 POSTGRES_PASSWORD로 DATABASE_URL 구성
    postgres_user = os.getenv("POSTGRES_USER", "trade_agent")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
    postgres_host = os.getenv("POSTGRES_HOST", "postgresql")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "upbit_metrics")
    DATABASE_URL: str = f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

# 애플리케이션 설정
APP_NAME: str = os.getenv("APP_NAME", "upbit-metrics-collector")
APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# API 설정
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# 수집기 설정
COLLECTION_INTERVAL_SECONDS: int = int(os.getenv("COLLECTION_INTERVAL_SECONDS", "1"))  # 1초마다 집계
ORDERBOOK_LEVELS: int = int(os.getenv("ORDERBOOK_LEVELS", "15"))  # 오더북 레벨 수
STANDARD_ORDER_SIZE_KRW: float = float(os.getenv("STANDARD_ORDER_SIZE_KRW", "1000000"))  # 표준 주문 크기 (1M KRW)


