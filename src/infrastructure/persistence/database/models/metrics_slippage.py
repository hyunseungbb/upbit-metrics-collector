"""
예상 슬리피지 평가지표 모델
"""
from datetime import datetime
import uuid

from sqlalchemy import Column, String, Numeric, DateTime, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import enum

from ..session import Base


class OrderSide(str, enum.Enum):
    """주문 방향"""
    BUY = "BUY"
    SELL = "SELL"


class MetricsSlippageModel(Base):
    """예상 슬리피지 평가지표 모델"""
    __tablename__ = "metrics_slippage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    order_size_krw = Column(Numeric(20, 2), nullable=False)  # 주문 크기 (KRW)
    side = Column(SQLEnum(OrderSide), nullable=False)  # 매수/매도
    slippage_bps = Column(Numeric(10, 4), nullable=False)  # 슬리피지 (bps)
    
    # 파생값
    slippage_bps_ema_30s = Column(Numeric(10, 4), nullable=True)  # 30초 EMA
    slippage_bps_mean_5m = Column(Numeric(10, 4), nullable=True)  # 5분 평균
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 복합 인덱스
    __table_args__ = (
        Index('idx_metrics_slippage_symbol_timestamp', 'symbol', 'timestamp'),
    )

    def __repr__(self):
        return f"<MetricsSlippageModel(symbol={self.symbol}, side={self.side}, slippage_bps={self.slippage_bps}, timestamp={self.timestamp})>"




