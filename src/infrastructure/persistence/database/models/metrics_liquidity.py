"""
24h 거래대금 평가지표 모델
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from ..session import Base


class MetricsLiquidityModel(Base):
    """24h 거래대금 평가지표 모델"""
    __tablename__ = "metrics_liquidity"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    acc_trade_price_24h = Column(Numeric(20, 2), nullable=False)  # 24시간 누적 거래대금
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 복합 인덱스
    __table_args__ = (
        Index('idx_metrics_liquidity_symbol_timestamp', 'symbol', 'timestamp'),
    )

    def __repr__(self):
        return f"<MetricsLiquidityModel(symbol={self.symbol}, acc_trade_price_24h={self.acc_trade_price_24h}, timestamp={self.timestamp})>"


