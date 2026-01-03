"""
Candle 데이터 수집기
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from ..infrastructure.adapters.candle import UpbitCandleAdapter
from ..domain.services.volatility_calculator import VolatilityCalculator
from ..infrastructure.persistence.database.session import AsyncSessionLocal
from ..infrastructure.persistence.database.models import MetricsVolatilityModel
from ..config.logging import logger


class CandleCollector:
    """Candle 데이터 수집기"""
    
    def __init__(self, unit: int = 1):
        """
        Args:
            unit: 캔들 단위 (분)
        """
        self.unit = unit
        self.adapter = UpbitCandleAdapter(unit=unit)
        self.calculator = VolatilityCalculator()
        self.running = False
        self.last_candle_timestamp: Dict[str, str] = {}
    
    async def start(self, symbols: List[str]) -> None:
        """수집 시작"""
        self.running = True
        logger.info("Candle 수집기 시작", symbols=symbols, unit=f"{self.unit}분")
        
        # WebSocket 구독
        try:
            await self.adapter.subscribe(symbols, self._on_candle_data)
            logger.info("Candle WebSocket 구독 완료", symbols=symbols)
        except Exception as e:
            logger.error("Candle WebSocket 구독 실패", error=str(e), symbols=symbols)
            raise
        
        # 주기적으로 변동성 계산 및 저장
        asyncio.create_task(self._calculate_loop())
        logger.info("Candle 계산 루프 시작")
    
    async def stop(self) -> None:
        """수집 중지"""
        logger.info("Candle 수집기 중지")
        self.running = False
        await self.adapter.disconnect()
    
    async def _on_candle_data(self, data: Dict[str, Any]) -> None:
        """Candle 데이터 수신 콜백"""
        symbol = data.get("code")
        candle_date_time_kst = data.get("candle_date_time_kst")
        
        # 새로운 캔들인지 확인 (같은 타임스탬프면 업데이트)
        if symbol and candle_date_time_kst:
            is_new_candle = symbol not in self.last_candle_timestamp or \
                           self.last_candle_timestamp[symbol] != candle_date_time_kst
            
            # 캔들 데이터 추가
            self.calculator.add_candle(data)
            
            if is_new_candle:
                # 새로운 캔들
                self.last_candle_timestamp[symbol] = candle_date_time_kst
                candle_count = len(self.calculator.candles.get(symbol, []))
                logger.info("새로운 캔들 수신", symbol=symbol, candle_time=candle_date_time_kst, candle_count=candle_count)
                
                # 캔들 데이터가 1개 이상이면 저장 시도 (range_1m은 최소 1개 캔들만 있어도 계산 가능)
                if candle_count >= 1:
                    await self._save_volatility(symbol)
                else:
                    logger.debug("캔들 데이터 부족, 저장 대기", symbol=symbol, candle_count=candle_count, required=1)
            else:
                # 같은 캔들 업데이트
                logger.debug("캔들 업데이트", symbol=symbol)
    
    async def _calculate_loop(self) -> None:
        """주기적으로 변동성 계산 및 저장"""
        while self.running:
            try:
                await asyncio.sleep(60)  # 1분마다
                
                # 모니터링 중인 모든 종목에 대해 변동성 계산 및 저장
                async with AsyncSessionLocal() as session:
                    try:
                        from sqlalchemy import select
                        from ..infrastructure.persistence.database.models import MonitoredSymbolsModel
                        
                        result = await session.execute(
                            select(MonitoredSymbolsModel).where(
                                MonitoredSymbolsModel.is_active == True
                            )
                        )
                        symbols = [row.symbol for row in result.scalars().all()]
                        
                        for symbol in symbols:
                            candle_count = len(self.calculator.candles.get(symbol, []))
                            if candle_count >= 1:
                                await self._save_volatility(symbol)
                            else:
                                logger.debug("주기적 계산: 캔들 데이터 부족", symbol=symbol, candle_count=candle_count, required=1)
                    except Exception as e:
                        logger.error("주기적 변동성 계산 오류", error=str(e), error_type=type(e).__name__)
            except Exception as e:
                logger.error("Candle 계산 루프 오류", error=str(e), error_type=type(e).__name__, exc_info=True)
    
    async def _save_volatility(self, symbol: str) -> None:
        """변동성 저장"""
        candle_count = len(self.calculator.candles.get(symbol, []))
        result = self.calculator.calculate(symbol)
        
        if not result:
            logger.debug("변동성 계산 결과 없음", symbol=symbol, candle_count=candle_count)
            return
        
        # 계산된 값 확인 및 로깅
        volatility_15m = result.get("volatility_15m")
        volatility_30m = result.get("volatility_30m")
        range_1m = result.get("range_1m")
        range_1m_mean_15m = result.get("range_1m_mean_15m")
        
        logger.debug(
            "변동성 계산 결과",
            symbol=symbol,
            candle_count=candle_count,
            volatility_15m=float(volatility_15m) if volatility_15m is not None else None,
            volatility_30m=float(volatility_30m) if volatility_30m is not None else None,
            range_1m=float(range_1m) if range_1m is not None else None,
            range_1m_mean_15m=float(range_1m_mean_15m) if range_1m_mean_15m is not None else None,
        )
        
        # 저장 조건: range_1m이 계산 가능하면 저장 (range_1m은 최소 1개 캔들만 있어도 계산 가능)
        # range_1m이 None이 아니거나, range_1m_mean_15m이 None이 아니면 저장
        has_data = (
            range_1m is not None or
            range_1m_mean_15m is not None or
            volatility_15m is not None or
            volatility_30m is not None
        )
        
        if not has_data:
            logger.debug("변동성 계산 결과에 유효한 값 없음", symbol=symbol, candle_count=candle_count)
            return
        
        async with AsyncSessionLocal() as session:
            try:
                volatility_model = MetricsVolatilityModel(
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    volatility_15m=volatility_15m,
                    volatility_30m=volatility_30m,
                    range_1m=range_1m,
                    range_1m_mean_15m=range_1m_mean_15m,
                )
                session.add(volatility_model)
                await session.commit()
                logger.info(
                    "변동성 저장 완료",
                    symbol=symbol,
                    candle_count=candle_count,
                    volatility_15m=float(volatility_15m) if volatility_15m is not None else None,
                    volatility_30m=float(volatility_30m) if volatility_30m is not None else None,
                    range_1m=float(range_1m) if range_1m is not None else None,
                    range_1m_mean_15m=float(range_1m_mean_15m) if range_1m_mean_15m is not None else None,
                )
            except Exception as e:
                await session.rollback()
                logger.error(
                    "변동성 저장 오류",
                    error=str(e),
                    symbol=symbol,
                    candle_count=candle_count,
                    error_type=type(e).__name__,
                    exc_info=True
                )


