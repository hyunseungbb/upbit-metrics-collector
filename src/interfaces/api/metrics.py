"""
평가지표 조회 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
from typing import Optional, List
from decimal import Decimal

from ...infrastructure.persistence.database.session import get_db
from ...infrastructure.persistence.database.models import (
    MetricsSpreadModel,
    MetricsOrderbookImbalanceModel,
    MetricsSlippageModel,
    MetricsTradeImbalanceModel,
    MetricsVolatilityModel,
    MetricsLiquidityModel,
)

router = APIRouter()


@router.get("/metrics/{symbol}")
async def get_metrics(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """종목별 최신 평가지표 조회"""
    try:
        # 각 평가지표의 최신 데이터 조회
        now = datetime.utcnow()
        
        # 스프레드
        spread_result = await db.execute(
            select(MetricsSpreadModel)
            .where(MetricsSpreadModel.symbol == symbol)
            .order_by(desc(MetricsSpreadModel.timestamp))
            .limit(1)
        )
        spread = spread_result.scalar_one_or_none()
        
        # 오더북 불균형
        imbalance_result = await db.execute(
            select(MetricsOrderbookImbalanceModel)
            .where(MetricsOrderbookImbalanceModel.symbol == symbol)
            .order_by(desc(MetricsOrderbookImbalanceModel.timestamp))
            .limit(1)
        )
        imbalance = imbalance_result.scalar_one_or_none()
        
        # 슬리피지 (매수/매도)
        slippage_buy_result = await db.execute(
            select(MetricsSlippageModel)
            .where(
                MetricsSlippageModel.symbol == symbol,
                MetricsSlippageModel.side == "BUY"
            )
            .order_by(desc(MetricsSlippageModel.timestamp))
            .limit(1)
        )
        slippage_buy = slippage_buy_result.scalar_one_or_none()
        
        slippage_sell_result = await db.execute(
            select(MetricsSlippageModel)
            .where(
                MetricsSlippageModel.symbol == symbol,
                MetricsSlippageModel.side == "SELL"
            )
            .order_by(desc(MetricsSlippageModel.timestamp))
            .limit(1)
        )
        slippage_sell = slippage_sell_result.scalar_one_or_none()
        
        # 체결 방향 비율 (1m=60s, 3m=180s, 5m=300s)
        trade_imbalance_1m_result = await db.execute(
            select(MetricsTradeImbalanceModel)
            .where(
                MetricsTradeImbalanceModel.symbol == symbol,
                MetricsTradeImbalanceModel.window_seconds == 60
            )
            .order_by(desc(MetricsTradeImbalanceModel.timestamp))
            .limit(1)
        )
        trade_imbalance_1m = trade_imbalance_1m_result.scalar_one_or_none()
        
        trade_imbalance_3m_result = await db.execute(
            select(MetricsTradeImbalanceModel)
            .where(
                MetricsTradeImbalanceModel.symbol == symbol,
                MetricsTradeImbalanceModel.window_seconds == 180
            )
            .order_by(desc(MetricsTradeImbalanceModel.timestamp))
            .limit(1)
        )
        trade_imbalance_3m = trade_imbalance_3m_result.scalar_one_or_none()
        
        trade_imbalance_5m_result = await db.execute(
            select(MetricsTradeImbalanceModel)
            .where(
                MetricsTradeImbalanceModel.symbol == symbol,
                MetricsTradeImbalanceModel.window_seconds == 300
            )
            .order_by(desc(MetricsTradeImbalanceModel.timestamp))
            .limit(1)
        )
        trade_imbalance_5m = trade_imbalance_5m_result.scalar_one_or_none()
        
        # 변동성
        volatility_result = await db.execute(
            select(MetricsVolatilityModel)
            .where(MetricsVolatilityModel.symbol == symbol)
            .order_by(desc(MetricsVolatilityModel.timestamp))
            .limit(1)
        )
        volatility = volatility_result.scalar_one_or_none()
        
        # 유동성
        liquidity_result = await db.execute(
            select(MetricsLiquidityModel)
            .where(MetricsLiquidityModel.symbol == symbol)
            .order_by(desc(MetricsLiquidityModel.timestamp))
            .limit(1)
        )
        liquidity = liquidity_result.scalar_one_or_none()
        
        return {
            "symbol": symbol,
            "timestamp": now.isoformat(),
            "spread": {
                "spread_bps": float(spread.spread_bps) if spread else None,
                "mid_price": float(spread.mid_price) if spread else None,
                "timestamp": spread.timestamp.isoformat() if spread else None,
            } if spread else None,
            "orderbook_imbalance": {
                "imbalance": float(imbalance.imbalance) if imbalance else None,
                "bid_volume": float(imbalance.bid_volume) if imbalance else None,
                "ask_volume": float(imbalance.ask_volume) if imbalance else None,
                "timestamp": imbalance.timestamp.isoformat() if imbalance else None,
            } if imbalance else None,
            "slippage": {
                "buy": {
                    "slippage_bps": float(slippage_buy.slippage_bps) if slippage_buy else None,
                    "timestamp": slippage_buy.timestamp.isoformat() if slippage_buy else None,
                } if slippage_buy else None,
                "sell": {
                    "slippage_bps": float(slippage_sell.slippage_bps) if slippage_sell else None,
                    "timestamp": slippage_sell.timestamp.isoformat() if slippage_sell else None,
                } if slippage_sell else None,
            },
            "trade_imbalance": {
                "1m": {
                    "ti": float(trade_imbalance_1m.ti) if trade_imbalance_1m else None,
                    "cvd": float(trade_imbalance_1m.cvd) if trade_imbalance_1m else None,
                    "timestamp": trade_imbalance_1m.timestamp.isoformat() if trade_imbalance_1m else None,
                } if trade_imbalance_1m else None,
                "3m": {
                    "ti": float(trade_imbalance_3m.ti) if trade_imbalance_3m else None,
                    "cvd": float(trade_imbalance_3m.cvd) if trade_imbalance_3m else None,
                    "timestamp": trade_imbalance_3m.timestamp.isoformat() if trade_imbalance_3m else None,
                } if trade_imbalance_3m else None,
                "5m": {
                    "ti": float(trade_imbalance_5m.ti) if trade_imbalance_5m else None,
                    "cvd": float(trade_imbalance_5m.cvd) if trade_imbalance_5m else None,
                    "timestamp": trade_imbalance_5m.timestamp.isoformat() if trade_imbalance_5m else None,
                } if trade_imbalance_5m else None,
            },
            "volatility": {
                "volatility_15m": float(volatility.volatility_15m) if volatility and volatility.volatility_15m else None,
                "volatility_30m": float(volatility.volatility_30m) if volatility and volatility.volatility_30m else None,
                "range_1m": float(volatility.range_1m) if volatility and volatility.range_1m else None,
                "timestamp": volatility.timestamp.isoformat() if volatility else None,
            } if volatility else None,
            "liquidity": {
                "acc_trade_price_24h": float(liquidity.acc_trade_price_24h) if liquidity else None,
                "timestamp": liquidity.timestamp.isoformat() if liquidity else None,
            } if liquidity else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/{symbol}/history")
async def get_metrics_history(
    symbol: str,
    metric_type: str = Query(..., description="평가지표 타입 (spread, orderbook_imbalance, slippage, trade_imbalance, volatility, liquidity)"),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """평가지표 시계열 조회"""
    try:
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        if metric_type == "spread":
            result = await db.execute(
                select(MetricsSpreadModel)
                .where(
                    MetricsSpreadModel.symbol == symbol,
                    MetricsSpreadModel.timestamp >= start_time,
                    MetricsSpreadModel.timestamp <= end_time,
                )
                .order_by(desc(MetricsSpreadModel.timestamp))
                .limit(limit)
            )
            items = result.scalars().all()
            return {
                "symbol": symbol,
                "metric_type": metric_type,
                "data": [
                    {
                        "timestamp": item.timestamp.isoformat(),
                        "spread_bps": float(item.spread_bps),
                        "mid_price": float(item.mid_price),
                    }
                    for item in items
                ],
            }
        elif metric_type == "orderbook_imbalance":
            result = await db.execute(
                select(MetricsOrderbookImbalanceModel)
                .where(
                    MetricsOrderbookImbalanceModel.symbol == symbol,
                    MetricsOrderbookImbalanceModel.timestamp >= start_time,
                    MetricsOrderbookImbalanceModel.timestamp <= end_time,
                )
                .order_by(desc(MetricsOrderbookImbalanceModel.timestamp))
                .limit(limit)
            )
            items = result.scalars().all()
            return {
                "symbol": symbol,
                "metric_type": metric_type,
                "data": [
                    {
                        "timestamp": item.timestamp.isoformat(),
                        "imbalance": float(item.imbalance),
                        "bid_volume": float(item.bid_volume),
                        "ask_volume": float(item.ask_volume),
                    }
                    for item in items
                ],
            }
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 평가지표 타입: {metric_type}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


