"""
스프레드 평가지표 모델
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from ..session import Base


class MetricsSpreadModel(Base):
    """스프레드 평가지표 모델"""
    __tablename__ = "metrics_spread"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)  # 예: KRW-BTC
    timestamp = Column(DateTime, nullable=False, index=True)
    spread_bps = Column(Numeric(10, 4), nullable=False)  # 스프레드 (bps)
    mid_price = Column(Numeric(20, 8), nullable=False)  # 중간가격
    
    # 파생값
    spread_bps_ema_10s = Column(Numeric(10, 4), nullable=True)  # 10초 EMA
    spread_bps_mean_60s = Column(Numeric(10, 4), nullable=True)  # 60초 평균
    spread_bps_p95_5m = Column(Numeric(10, 4), nullable=True)  # 5분 95퍼센타일
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 복합 인덱스
    __table_args__ = (
        Index('idx_metrics_spread_symbol_timestamp', 'symbol', 'timestamp'),
    )

    def __repr__(self):
        return f"<MetricsSpreadModel(symbol={self.symbol}, spread_bps={self.spread_bps}, timestamp={self.timestamp})>"




