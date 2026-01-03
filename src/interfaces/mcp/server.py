"""
FastMCP를 사용한 MCP 서버
업비트 평가지표 수집 시스템의 데이터를 MCP tools로 노출
"""
from fastmcp import FastMCP
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from typing import Optional
from decimal import Decimal

from ...infrastructure.persistence.database.session import AsyncSessionLocal
from ...infrastructure.persistence.database.models import OrderSide, MonitoredSymbolsModel
from ...application.services.metrics_query import (
    get_latest_metrics_for_symbols,
    calculate_staleness_and_freshness,
    get_metrics_summary,
)
from ...config.logging import logger
from sqlalchemy import select

# MCP 서버 인스턴스 생성
mcp = FastMCP("Upbit Metrics Collector")


async def get_db_session() -> AsyncSession:
    """데이터베이스 세션 생성"""
    return AsyncSessionLocal()


@mcp.tool()
async def get_monitored_symbols(is_active: bool = True) -> dict:
    """
    활성 모니터링 종목 목록을 조회합니다.
    
    Args:
        is_active: 활성 종목만 조회할지 여부 (기본값: True)
    
    Returns:
        {
            "symbols": ["KRW-BTC", "KRW-ETH", ...],
            "count": 3,
            "as_of": "2026-01-03T11:30:00+09:00"
        }
    """
    async with AsyncSessionLocal() as session:
        try:
            query = select(MonitoredSymbolsModel)
            if is_active:
                query = query.where(MonitoredSymbolsModel.is_active == True)
            
            result = await session.execute(query)
            symbols_list = [s.symbol for s in result.scalars().all()]
            
            # 한국 시간대 (UTC+9)
            now_kst = datetime.now(timezone(timedelta(hours=9)))
            
            return {
                "symbols": symbols_list,
                "count": len(symbols_list),
                "as_of": now_kst.isoformat(),
            }
        except Exception as e:
            logger.error(
                "심볼 목록 조회 오류",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise


@mcp.tool()
async def get_latest_metrics(
    symbols: str,
    order_size_krw: float,
    slippage_side: str = "BUY",
    ti_windows_sec: str = "30,60",
    freshness_ms: int = 5000,
) -> dict:
    """
    여러 심볼의 최신 평가지표를 한 번에 조회합니다 (원샷 번들).
    
    각 심볼별로 6개 지표의 최신 row를 합쳐서 반환합니다:
    - liquidity: 24h 거래대금
    - spread: 스프레드 및 EMA, p95
    - orderbook_imbalance: 불균형 및 EMA, z-score
    - slippage: 슬리피지 및 EMA, mean
    - trade_imbalance: 여러 윈도우의 TI, CVD
    - volatility: 변동성 지표
    
    Args:
        symbols: 조회할 심볼 목록 (comma-separated, 예: "KRW-BTC,KRW-ETH")
        order_size_krw: 슬리피지 계산용 주문 크기 (KRW)
        slippage_side: 슬리피지 방향 (BUY/SELL, 기본값: BUY)
        ti_windows_sec: trade imbalance 윈도우 (초 단위, comma-separated, 기본값: "30,60")
        freshness_ms: 데이터 신선도 기준 (밀리초, 기본값: 5000)
    
    Returns:
        {
            "freshness_ms": 5000,
            "data": [
                {
                    "symbol": "KRW-BTC",
                    "as_of": "...",
                    "staleness_ms": 100,
                    "is_fresh": true,
                    "liquidity": {...},
                    "spread": {...},
                    "orderbook_imbalance": {...},
                    "slippage": {...},
                    "trade_imbalance": [...],
                    "volatility": {...},
                    "ti_30s": "...",
                    "ti_60s": "...",
                    "cvd_30s": "...",
                    "cvd_60s": "..."
                }
            ]
        }
    """
    async with AsyncSessionLocal() as session:
        try:
            # 파라미터 파싱
            symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
            if not symbol_list:
                raise ValueError("symbols 파라미터가 필요합니다")
            
            order_size = Decimal(str(order_size_krw))
            
            try:
                side = OrderSide(slippage_side.upper())
            except ValueError:
                raise ValueError(f"잘못된 slippage_side: {slippage_side}")
            
            ti_windows = [int(w.strip()) for w in ti_windows_sec.split(",") if w.strip()]
            if not ti_windows:
                ti_windows = [30, 60]
            
            # 데이터 조회
            query_time = datetime.utcnow()
            metrics_dict = await get_latest_metrics_for_symbols(
                session=session,
                symbols=symbol_list,
                order_size_krw=order_size,
                slippage_side=side,
                ti_windows_sec=ti_windows,
            )
            
            # 응답 형식 변환
            data = []
            for symbol in symbol_list:
                metrics = metrics_dict.get(symbol, {})
                
                # 신선도 계산
                staleness_ms, is_fresh = calculate_staleness_and_freshness(
                    metrics=metrics,
                    freshness_ms=freshness_ms,
                    query_time=query_time,
                )
                
                symbol_data = {
                    "symbol": symbol,
                    "as_of": query_time.isoformat(),
                    "staleness_ms": staleness_ms,
                    "is_fresh": is_fresh,
                }
                
                # 각 지표 추가
                if "liquidity" in metrics:
                    symbol_data["liquidity"] = metrics["liquidity"]
                
                if "spread" in metrics:
                    symbol_data["spread"] = metrics["spread"]
                
                if "orderbook_imbalance" in metrics:
                    symbol_data["orderbook_imbalance"] = metrics["orderbook_imbalance"]
                
                if "slippage" in metrics:
                    symbol_data["slippage"] = metrics["slippage"]
                
                if "trade_imbalance" in metrics:
                    symbol_data["trade_imbalance"] = metrics["trade_imbalance"]
                    
                    # trade_imbalance 배열을 순회하여 플랫한 키 추가
                    for ti_item in metrics["trade_imbalance"]:
                        window_sec = ti_item.get("window_sec")
                        if window_sec is not None:
                            symbol_data[f"ti_{window_sec}s"] = ti_item.get("ti")
                            symbol_data[f"cvd_{window_sec}s"] = ti_item.get("cvd")
                
                # volatility는 항상 추가 (데이터가 없을 경우 빈 객체)
                if "volatility" in metrics:
                    symbol_data["volatility"] = metrics["volatility"]
                else:
                    # 데이터가 없을 경우 빈 객체 반환
                    symbol_data["volatility"] = {
                        "volatility_15m": None,
                        "volatility_30m": None,
                        "range_1m_mean_15m": None,
                        "as_of": None,
                    }
                
                data.append(symbol_data)
            
            return {
                "freshness_ms": freshness_ms,
                "data": data,
            }
            
        except Exception as e:
            logger.error(
                "최신 지표 번들 조회 오류",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise


@mcp.tool()
async def get_metrics_summary(
    symbol: str,
    order_size_krw: float,
    lookback_sec: int = 600,
    slippage_side: str = "BUY",
    ti_windows_sec: str = "30,60",
) -> dict:
    """
    최근 구간의 평가지표 요약을 조회합니다.
    
    lookback_sec 기간의 데이터를 기반으로 min, max, mean, last 등의 통계를 제공합니다.
    이미 저장된 EMA/p95 값을 활용하여 추가 집계를 최소화합니다.
    
    Args:
        symbol: 조회할 심볼 (예: "KRW-BTC")
        order_size_krw: 슬리피지 계산용 주문 크기 (KRW)
        lookback_sec: 최근 N초 (기본값: 600초 = 10분)
        slippage_side: 슬리피지 방향 (BUY/SELL, 기본값: BUY)
        ti_windows_sec: trade imbalance 윈도우 (초 단위, comma-separated, 기본값: "30,60")
    
    Returns:
        {
            "symbol": "KRW-BTC",
            "lookback_sec": 600,
            "as_of": "...",
            "spread": {...},
            "slippage": {...},
            "imbalance": {...},
            "ti_30s": {...},
            "ti_60s": {...},
            "volatility": {...},
            "liquidity": {...}
        }
    """
    async with AsyncSessionLocal() as session:
        try:
            # 파라미터 파싱
            order_size = Decimal(str(order_size_krw))
            
            try:
                side = OrderSide(slippage_side.upper())
            except ValueError:
                raise ValueError(f"잘못된 slippage_side: {slippage_side}")
            
            ti_windows = [int(w.strip()) for w in ti_windows_sec.split(",") if w.strip()]
            if not ti_windows:
                ti_windows = [30, 60]
            
            # 데이터 조회
            query_time = datetime.utcnow()
            from ...application.services.metrics_query import get_metrics_summary as get_metrics_summary_service
            summary = await get_metrics_summary_service(
                session=session,
                symbol=symbol.upper(),
                lookback_sec=lookback_sec,
                order_size_krw=order_size,
                slippage_side=side,
                ti_windows_sec=ti_windows,
            )
            
            return {
                "symbol": symbol.upper(),
                "lookback_sec": lookback_sec,
                "as_of": query_time.isoformat(),
                **summary,
            }
            
        except Exception as e:
            logger.error(
                "요약 통계 조회 오류",
                symbol=symbol,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise


if __name__ == "__main__":
    mcp.run()

