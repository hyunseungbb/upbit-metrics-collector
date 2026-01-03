"""
오더북 불균형 평가지표 모델
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from ..session import Base


class MetricsOrderbookImbalanceModel(Base):
    """오더북 불균형 평가지표 모델"""
    __tablename__ = "metrics_orderbook_imbalance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    imbalance = Column(Numeric(5, 4), nullable=False)  # 0~1 사이 값
    bid_volume = Column(Numeric(20, 8), nullable=False)  # 매수 호가 총량
    ask_volume = Column(Numeric(20, 8), nullable=False)  # 매도 호가 총량
    
    # 파생값
    imbalance_ema_5s = Column(Numeric(5, 4), nullable=True)  # 5초 EMA
    imbalance_ema_30s = Column(Numeric(5, 4), nullable=True)  # 30초 EMA
    imbalance_mean_5m = Column(Numeric(5, 4), nullable=True)  # 5분 평균
    imbalance_zscore_24h = Column(Numeric(10, 4), nullable=True)  # 24시간 Z-score
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 복합 인덱스
    __table_args__ = (
        Index('idx_metrics_orderbook_imbalance_symbol_timestamp', 'symbol', 'timestamp'),
    )

    def __repr__(self):
        return f"<MetricsOrderbookImbalanceModel(symbol={self.symbol}, imbalance={self.imbalance}, timestamp={self.timestamp})>"


