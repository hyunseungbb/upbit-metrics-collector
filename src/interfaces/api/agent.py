"""
에이전트용 평가지표 API
MCP 서버로 호출 가능한 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from ...infrastructure.persistence.database.session import get_db
from ...infrastructure.persistence.database.models import OrderSide
from ...application.services.metrics_query import (
    get_latest_metrics_for_symbols,
    calculate_staleness_and_freshness,
    get_metrics_summary,
)
from ...config.logging import logger
from ...infrastructure.persistence.database.models import MonitoredSymbolsModel
from sqlalchemy import select

router = APIRouter()


@router.get("/symbols")
async def get_symbols_v1(
    is_active: Optional[bool] = Query(True, description="활성 종목만 조회"),
    db: AsyncSession = Depends(get_db),
):
    """
    활성 모니터링 종목 조회 (에이전트용)
    
    Response 형식:
    {
      "symbols": ["KRW-BTC", "KRW-ETH", "KRW-XRP"],
      "count": 3,
      "as_of": "2026-01-03T11:30:00+09:00"
    }
    """
    try:
        from datetime import timezone, timedelta
        
        query = select(MonitoredSymbolsModel)
        if is_active:
            query = query.where(MonitoredSymbolsModel.is_active == True)
        
        result = await db.execute(query)
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/metrics/latest")
async def get_latest_metrics_bundle(
    symbols: str = Query(..., description="조회할 심볼 목록 (comma-separated)"),
    order_size_krw: float = Query(..., description="슬리피지 계산용 주문 크기 (KRW)"),
    slippage_side: str = Query("BUY", description="슬리피지 방향 (BUY/SELL)"),
    ti_windows_sec: str = Query("30,60", description="trade imbalance 윈도우 (초 단위, comma-separated)"),
    freshness_ms: int = Query(5000, description="데이터 신선도 기준 (밀리초)"),
    db: AsyncSession = Depends(get_db),
):
    """
    여러 심볼의 최신 평가지표를 한 번에 조회합니다 (원샷 번들).
    
    각 심볼별로 6개 지표의 최신 row를 합쳐서 반환합니다:
    - liquidity: 24h 거래대금
    - spread: 스프레드 및 EMA, p95
    - orderbook_imbalance: 불균형 및 EMA, z-score
    - slippage: 슬리피지 및 EMA, mean
    - trade_imbalance: 여러 윈도우의 TI, CVD
    - volatility: 변동성 지표
    """
    try:
        # 파라미터 파싱
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            raise HTTPException(status_code=400, detail="symbols 파라미터가 필요합니다")
        
        order_size = Decimal(str(order_size_krw))
        
        try:
            side = OrderSide(slippage_side.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"잘못된 slippage_side: {slippage_side}")
        
        ti_windows = [int(w.strip()) for w in ti_windows_sec.split(",") if w.strip()]
        if not ti_windows:
            ti_windows = [30, 60]
        
        # 데이터 조회
        query_time = datetime.utcnow()
        metrics_dict = await get_latest_metrics_for_symbols(
            session=db,
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "최신 지표 번들 조회 오류",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/metrics/summary")
async def get_metrics_summary_endpoint(
    symbol: str = Query(..., description="조회할 심볼"),
    lookback_sec: int = Query(600, description="최근 N초 (기본값: 600초 = 10분)"),
    order_size_krw: float = Query(..., description="슬리피지 계산용 주문 크기 (KRW)"),
    slippage_side: str = Query("BUY", description="슬리피지 방향 (BUY/SELL)"),
    ti_windows_sec: str = Query("30,60", description="trade imbalance 윈도우 (초 단위, comma-separated)"),
    db: AsyncSession = Depends(get_db),
):
    """
    최근 구간의 평가지표 요약을 조회합니다.
    
    lookback_sec 기간의 데이터를 기반으로 min, max, mean, last 등의 통계를 제공합니다.
    이미 저장된 EMA/p95 값을 활용하여 추가 집계를 최소화합니다.
    """
    try:
        # 파라미터 파싱
        order_size = Decimal(str(order_size_krw))
        
        try:
            side = OrderSide(slippage_side.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"잘못된 slippage_side: {slippage_side}")
        
        ti_windows = [int(w.strip()) for w in ti_windows_sec.split(",") if w.strip()]
        if not ti_windows:
            ti_windows = [30, 60]
        
        # 데이터 조회
        query_time = datetime.utcnow()
        summary = await get_metrics_summary(
            session=db,
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "요약 통계 조회 오류",
            symbol=symbol,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))

