"""
에이전트용 평가지표 조회 서비스
여러 심볼의 최신 지표를 효율적으로 조회하고 통계를 계산합니다.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_

from ...infrastructure.persistence.database.models import (
    MetricsSpreadModel,
    MetricsOrderbookImbalanceModel,
    MetricsSlippageModel,
    MetricsTradeImbalanceModel,
    MetricsVolatilityModel,
    MetricsLiquidityModel,
    OrderSide,
)
from ...config.logging import logger


async def get_latest_metrics_for_symbols(
    session: AsyncSession,
    symbols: List[str],
    order_size_krw: Decimal,
    slippage_side: OrderSide = OrderSide.BUY,
    ti_windows_sec: List[int] = [30, 60],
) -> Dict[str, Dict[str, Any]]:
    """
    여러 심볼의 최신 평가지표를 조회합니다.
    
    Args:
        session: 데이터베이스 세션
        symbols: 조회할 심볼 목록
        order_size_krw: 슬리피지 계산용 주문 크기
        slippage_side: 슬리피지 방향 (BUY/SELL)
        ti_windows_sec: trade imbalance 윈도우 (초 단위)
    
    Returns:
        심볼별 최신 지표 딕셔너리
    """
    result = {}
    
    for symbol in symbols:
        try:
            # 각 지표별로 최신 row 조회
            metrics = {}
            
            # 1. Spread
            spread_result = await session.execute(
                select(MetricsSpreadModel)
                .where(MetricsSpreadModel.symbol == symbol)
                .order_by(desc(MetricsSpreadModel.timestamp))
                .limit(1)
            )
            spread = spread_result.scalar_one_or_none()
            if spread:
                metrics["spread"] = {
                    "spread_bps": str(spread.spread_bps),
                    "spread_bps_ema_10s": str(spread.spread_bps_ema_10s) if spread.spread_bps_ema_10s else None,
                    "spread_bps_p95_5m": str(spread.spread_bps_p95_5m) if spread.spread_bps_p95_5m else None,
                    "mid_price": str(spread.mid_price),
                    "as_of": spread.timestamp.isoformat(),
                }
            
            # 2. Orderbook Imbalance
            imbalance_result = await session.execute(
                select(MetricsOrderbookImbalanceModel)
                .where(MetricsOrderbookImbalanceModel.symbol == symbol)
                .order_by(desc(MetricsOrderbookImbalanceModel.timestamp))
                .limit(1)
            )
            imbalance = imbalance_result.scalar_one_or_none()
            if imbalance:
                metrics["orderbook_imbalance"] = {
                    "imbalance": str(imbalance.imbalance),
                    "imbalance_ema_5s": str(imbalance.imbalance_ema_5s) if imbalance.imbalance_ema_5s else None,
                    "imbalance_ema_30s": str(imbalance.imbalance_ema_30s) if imbalance.imbalance_ema_30s else None,
                    "imbalance_zscore_24h": str(imbalance.imbalance_zscore_24h) if imbalance.imbalance_zscore_24h else None,
                    "bid_volume": str(imbalance.bid_volume),
                    "ask_volume": str(imbalance.ask_volume),
                    "as_of": imbalance.timestamp.isoformat(),
                }
            
            # 3. Slippage (order_size_krw와 side에 맞는 것)
            # 먼저 정확히 일치하는 값을 찾고, 없으면 가장 가까운 값을 찾음
            slippage_result = await session.execute(
                select(MetricsSlippageModel)
                .where(
                    and_(
                        MetricsSlippageModel.symbol == symbol,
                        MetricsSlippageModel.order_size_krw == order_size_krw,
                        MetricsSlippageModel.side == slippage_side,
                    )
                )
                .order_by(desc(MetricsSlippageModel.timestamp))
                .limit(1)
            )
            slippage = slippage_result.scalar_one_or_none()
            
            # 정확히 일치하는 값이 없으면 가장 가까운 order_size_krw 값을 찾음
            if not slippage:
                all_slippage_result = await session.execute(
                    select(MetricsSlippageModel)
                    .where(
                        and_(
                            MetricsSlippageModel.symbol == symbol,
                            MetricsSlippageModel.side == slippage_side,
                        )
                    )
                    .order_by(desc(MetricsSlippageModel.timestamp))
                )
                all_slippages = all_slippage_result.scalars().all()
                
                if all_slippages:
                    # 가장 가까운 order_size_krw 값을 찾음
                    closest_slippage = min(
                        all_slippages,
                        key=lambda s: abs(float(s.order_size_krw) - float(order_size_krw))
                    )
                    slippage = closest_slippage
            
            if slippage:
                metrics["slippage"] = {
                    "order_size_krw": str(slippage.order_size_krw),
                    "side": slippage.side.value,
                    "slippage_bps": str(slippage.slippage_bps),
                    "slippage_bps_ema_30s": str(slippage.slippage_bps_ema_30s) if slippage.slippage_bps_ema_30s else None,
                    "slippage_bps_mean_5m": str(slippage.slippage_bps_mean_5m) if slippage.slippage_bps_mean_5m else None,
                    "as_of": slippage.timestamp.isoformat(),
                }
            
            # 4. Trade Imbalance (ti_windows_sec에 맞는 것)
            # 30초와 60초는 모두 window_minutes=1로 저장되므로, 각각 별도로 조회
            trade_imbalances = []
            
            # window_minutes=1인 최신 데이터를 가져옴 (30초와 60초 모두 포함)
            ti_result = await session.execute(
                select(MetricsTradeImbalanceModel)
                .where(
                    and_(
                        MetricsTradeImbalanceModel.symbol == symbol,
                        MetricsTradeImbalanceModel.window_minutes == 1,
                    )
                )
                .order_by(desc(MetricsTradeImbalanceModel.timestamp))
                .limit(1)
            )
            ti = ti_result.scalar_one_or_none()
            
            # 요청한 각 window_sec에 대해 데이터 추가
            # 현재 구조상 30초와 60초를 구분할 수 없으므로, 같은 데이터를 사용하되 window_sec는 다르게 설정
            if ti:
                for window_sec in ti_windows_sec:
                    # window_minutes=1인 경우 (30초 또는 60초)
                    window_min = window_sec // 60 if window_sec >= 60 else 1
                    if window_min == 1:
                        trade_imbalances.append({
                            "window_sec": window_sec,
                            "ti": str(ti.ti),
                            "cvd": str(ti.cvd),
                            "as_of": ti.timestamp.isoformat(),
                        })
                    else:
                        # window_minutes > 1인 경우 별도 조회
                        ti_result_long = await session.execute(
                            select(MetricsTradeImbalanceModel)
                            .where(
                                and_(
                                    MetricsTradeImbalanceModel.symbol == symbol,
                                    MetricsTradeImbalanceModel.window_minutes == window_min,
                                )
                            )
                            .order_by(desc(MetricsTradeImbalanceModel.timestamp))
                            .limit(1)
                        )
                        ti_long = ti_result_long.scalar_one_or_none()
                        if ti_long:
                            trade_imbalances.append({
                                "window_sec": window_sec,
                                "ti": str(ti_long.ti),
                                "cvd": str(ti_long.cvd),
                                "as_of": ti_long.timestamp.isoformat(),
                            })
            
            if trade_imbalances:
                metrics["trade_imbalance"] = trade_imbalances
            
            # 5. Volatility
            volatility_result = await session.execute(
                select(MetricsVolatilityModel)
                .where(MetricsVolatilityModel.symbol == symbol)
                .order_by(desc(MetricsVolatilityModel.timestamp))
                .limit(1)
            )
            volatility = volatility_result.scalar_one_or_none()
            if volatility:
                metrics["volatility"] = {
                    "volatility_15m": str(volatility.volatility_15m) if volatility.volatility_15m else None,
                    "volatility_30m": str(volatility.volatility_30m) if volatility.volatility_30m else None,
                    "range_1m_mean_15m": str(volatility.range_1m_mean_15m) if volatility.range_1m_mean_15m else None,
                    "as_of": volatility.timestamp.isoformat(),
                }
            else:
                # 데이터가 없을 경우 빈 객체 반환
                metrics["volatility"] = {
                    "volatility_15m": None,
                    "volatility_30m": None,
                    "range_1m_mean_15m": None,
                    "as_of": None,
                }
            
            # 6. Liquidity
            liquidity_result = await session.execute(
                select(MetricsLiquidityModel)
                .where(MetricsLiquidityModel.symbol == symbol)
                .order_by(desc(MetricsLiquidityModel.timestamp))
                .limit(1)
            )
            liquidity = liquidity_result.scalar_one_or_none()
            if liquidity:
                metrics["liquidity"] = {
                    "acc_trade_price_24h": str(liquidity.acc_trade_price_24h),
                    "as_of": liquidity.timestamp.isoformat(),
                }
            
            result[symbol] = metrics
            
        except Exception as e:
            logger.error(
                "심볼 지표 조회 오류",
                symbol=symbol,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            result[symbol] = {}
    
    return result


def calculate_staleness_and_freshness(
    metrics: Dict[str, Any],
    freshness_ms: int,
    query_time: datetime,
) -> Tuple[int, bool]:
    """
    지표의 신선도를 계산합니다.
    
    Args:
        metrics: 심볼별 지표 딕셔너리
        freshness_ms: 신선도 기준 (밀리초)
        query_time: 조회 시각
    
    Returns:
        (staleness_ms, is_fresh) 튜플
    """
    if not metrics:
        return 0, False
    
    max_staleness_ms = 0
    
    for metric_type, metric_data in metrics.items():
        if metric_type == "trade_imbalance":
            # trade_imbalance는 배열
            for ti_item in metric_data:
                if "as_of" in ti_item and ti_item["as_of"] is not None:
                    as_of = datetime.fromisoformat(ti_item["as_of"].replace("Z", "+00:00"))
                    staleness_ms = int((query_time - as_of).total_seconds() * 1000)
                    max_staleness_ms = max(max_staleness_ms, staleness_ms)
        else:
            # 단일 객체
            if metric_data and "as_of" in metric_data and metric_data["as_of"] is not None:
                as_of = datetime.fromisoformat(metric_data["as_of"].replace("Z", "+00:00"))
                staleness_ms = int((query_time - as_of).total_seconds() * 1000)
                max_staleness_ms = max(max_staleness_ms, staleness_ms)
    
    is_fresh = max_staleness_ms <= freshness_ms
    
    return max_staleness_ms, is_fresh


async def get_metrics_summary(
    session: AsyncSession,
    symbol: str,
    lookback_sec: int,
    order_size_krw: Decimal,
    slippage_side: OrderSide = OrderSide.BUY,
    ti_windows_sec: List[int] = [30, 60],
) -> Dict[str, Any]:
    """
    최근 구간의 평가지표 요약을 조회합니다.
    
    Args:
        session: 데이터베이스 세션
        symbol: 조회할 심볼
        lookback_sec: 조회 기간 (초)
        order_size_krw: 슬리피지 계산용 주문 크기
        slippage_side: 슬리피지 방향
        ti_windows_sec: trade imbalance 윈도우
    
    Returns:
        요약 통계 딕셔너리
    """
    cutoff_time = datetime.utcnow() - timedelta(seconds=lookback_sec)
    summary = {}
    
    try:
        # 1. Spread 통계
        spread_result = await session.execute(
            select(
                MetricsSpreadModel.spread_bps,
                MetricsSpreadModel.spread_bps_ema_10s,
                MetricsSpreadModel.spread_bps_p95_5m,
            )
            .where(
                and_(
                    MetricsSpreadModel.symbol == symbol,
                    MetricsSpreadModel.timestamp >= cutoff_time,
                )
            )
            .order_by(desc(MetricsSpreadModel.timestamp))
        )
        spreads = spread_result.all()
        
        if spreads:
            spread_values = [float(row[0]) for row in spreads]
            last_spread = spreads[0]
            summary["spread"] = {
                "last": float(last_spread[0]),
                "mean": sum(spread_values) / len(spread_values),
                "p95": float(last_spread[2]) if last_spread[2] else None,
                "max": max(spread_values),
                "min": min(spread_values),
            }
        
        # 2. Slippage 통계
        slippage_result = await session.execute(
            select(MetricsSlippageModel.slippage_bps, MetricsSlippageModel.slippage_bps_mean_5m)
            .where(
                and_(
                    MetricsSlippageModel.symbol == symbol,
                    MetricsSlippageModel.order_size_krw == order_size_krw,
                    MetricsSlippageModel.side == slippage_side,
                    MetricsSlippageModel.timestamp >= cutoff_time,
                )
            )
            .order_by(desc(MetricsSlippageModel.timestamp))
        )
        slippages = slippage_result.all()
        
        if slippages:
            slippage_values = [float(row[0]) for row in slippages]
            last_slippage = slippages[0]
            summary["slippage"] = {
                "last": float(last_slippage[0]),
                "p95": float(last_slippage[1]) if last_slippage[1] else None,
            }
        
        # 3. Orderbook Imbalance 통계
        imbalance_result = await session.execute(
            select(
                MetricsOrderbookImbalanceModel.imbalance,
                MetricsOrderbookImbalanceModel.imbalance_ema_30s,
            )
            .where(
                and_(
                    MetricsOrderbookImbalanceModel.symbol == symbol,
                    MetricsOrderbookImbalanceModel.timestamp >= cutoff_time,
                )
            )
            .order_by(desc(MetricsOrderbookImbalanceModel.timestamp))
        )
        imbalances = imbalance_result.all()
        
        if imbalances:
            imbalance_values = [float(row[0]) for row in imbalances]
            last_imbalance = imbalances[0]
            summary["imbalance"] = {
                "last": float(last_imbalance[0]),
                "ema_30s": float(last_imbalance[1]) if last_imbalance[1] else None,
                "min": min(imbalance_values),
                "max": max(imbalance_values),
            }
        
        # 4. Trade Imbalance 통계 (ti_windows_sec에 맞는 것)
        ti_windows_minutes = []
        for sec in ti_windows_sec:
            if sec <= 30:
                ti_windows_minutes.append(1)
            elif sec <= 60:
                ti_windows_minutes.append(1)
            else:
                ti_windows_minutes.append(sec // 60)
        
        for window_sec in ti_windows_sec:
            window_min = 1 if window_sec <= 60 else window_sec // 60
            ti_result = await session.execute(
                select(MetricsTradeImbalanceModel.ti)
                .where(
                    and_(
                        MetricsTradeImbalanceModel.symbol == symbol,
                        MetricsTradeImbalanceModel.window_minutes == window_min,
                        MetricsTradeImbalanceModel.timestamp >= cutoff_time,
                    )
                )
                .order_by(desc(MetricsTradeImbalanceModel.timestamp))
            )
            ti_values = [float(row[0]) for row in ti_result.all()]
            
            if ti_values:
                summary[f"ti_{window_sec}s"] = {
                    "last": ti_values[0],
                    "mean": sum(ti_values) / len(ti_values),
                }
        
        # 5. Volatility (최신 값만)
        volatility_result = await session.execute(
            select(
                MetricsVolatilityModel.volatility_15m,
                MetricsVolatilityModel.volatility_30m,
            )
            .where(MetricsVolatilityModel.symbol == symbol)
            .order_by(desc(MetricsVolatilityModel.timestamp))
            .limit(1)
        )
        volatility = volatility_result.scalar_one_or_none()
        
        if volatility:
            summary["volatility"] = {
                "vol_15m": float(volatility[0]) if volatility[0] else None,
                "vol_30m": float(volatility[1]) if volatility[1] else None,
            }
        
        # 6. Liquidity (최신 값만)
        liquidity_result = await session.execute(
            select(MetricsLiquidityModel.acc_trade_price_24h)
            .where(MetricsLiquidityModel.symbol == symbol)
            .order_by(desc(MetricsLiquidityModel.timestamp))
            .limit(1)
        )
        liquidity = liquidity_result.scalar_one_or_none()
        
        if liquidity:
            summary["liquidity"] = {
                "acc_trade_price_24h": float(liquidity),
            }
        
    except Exception as e:
        logger.error(
            "요약 통계 조회 오류",
            symbol=symbol,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
    
    return summary

