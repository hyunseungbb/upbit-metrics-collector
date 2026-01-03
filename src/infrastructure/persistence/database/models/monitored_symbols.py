"""
모니터링 종목 모델
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from ..session import Base


class MonitoredSymbolsModel(Base):
    """모니터링 종목 모델"""
    __tablename__ = "monitored_symbols"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, unique=True, index=True)  # 예: KRW-BTC
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<MonitoredSymbolsModel(symbol={self.symbol}, is_active={self.is_active})>"


