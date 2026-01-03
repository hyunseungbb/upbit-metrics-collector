"""
단기 변동성 평가지표 모델
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from ..session import Base


class MetricsVolatilityModel(Base):
    """단기 변동성 평가지표 모델"""
    __tablename__ = "metrics_volatility"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    volatility_15m = Column(Numeric(10, 6), nullable=True)  # 15분 변동성
    volatility_30m = Column(Numeric(10, 6), nullable=True)  # 30분 변동성
    range_1m = Column(Numeric(10, 6), nullable=True)  # 1분 범위 (high-low)/open
    
    # 파생값
    range_1m_mean_15m = Column(Numeric(10, 6), nullable=True)  # 15분 평균 범위
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 복합 인덱스
    __table_args__ = (
        Index('idx_metrics_volatility_symbol_timestamp', 'symbol', 'timestamp'),
    )

    def __repr__(self):
        return f"<MetricsVolatilityModel(symbol={self.symbol}, volatility_15m={self.volatility_15m}, timestamp={self.timestamp})>"


