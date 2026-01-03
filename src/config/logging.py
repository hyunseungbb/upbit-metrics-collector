"""
로깅 설정
"""
import logging
import sys
from pathlib import Path

import structlog
from structlog.stdlib import LoggerFactory

from .env_config import LOG_LEVEL

# 로그 디렉토리 생성
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Structlog 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if LOG_LEVEL == "DEBUG" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# 파일 핸들러 추가
file_handler = logging.FileHandler(LOG_DIR / "collector.log", encoding="utf-8")
file_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
file_handler.setFormatter(logging.Formatter("%(message)s"))

# 표준 로깅 설정
logging.basicConfig(
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout), file_handler],
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)

# 로거 가져오기
logger = structlog.get_logger(__name__)

