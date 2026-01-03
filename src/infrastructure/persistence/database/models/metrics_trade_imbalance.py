"""
체결 방향 비율 평가지표 모델
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Numeric, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID

from ..session import Base


class MetricsTradeImbalanceModel(Base):
    """체결 방향 비율 평가지표 모델"""
    __tablename__ = "metrics_trade_imbalance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    window_minutes = Column(Integer, nullable=False)  # 윈도우 크기 (1/3/5분)
    buy_volume = Column(Numeric(20, 8), nullable=False)  # 매수 체결량
    sell_volume = Column(Numeric(20, 8), nullable=False)  # 매도 체결량
    ti = Column(Numeric(5, 4), nullable=False)  # Trade Imbalance (0~1)
    cvd = Column(Numeric(20, 8), nullable=False)  # Cumulative Volume Delta (buy_volume - sell_volume)
    
    # 파생값 (별도 컬럼으로 저장하지 않고 window_minutes로 구분)
    # ti_1m, ti_3m, ti_5m은 window_minutes로 구분
    # cvd_1m, cvd_5m도 window_minutes로 구분
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 복합 인덱스
    __table_args__ = (
        Index('idx_metrics_trade_imbalance_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_metrics_trade_imbalance_symbol_window', 'symbol', 'window_minutes'),
    )

    def __repr__(self):
        return f"<MetricsTradeImbalanceModel(symbol={self.symbol}, window={self.window_minutes}m, ti={self.ti}, timestamp={self.timestamp})>"


