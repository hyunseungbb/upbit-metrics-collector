"""
Trade 데이터 수집기
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..infrastructure.adapters.trade import UpbitTradeAdapter
from ..domain.services.trade_imbalance_calculator import TradeImbalanceCalculator
from ..infrastructure.persistence.database.session import AsyncSessionLocal
from ..infrastructure.persistence.database.models import MetricsTradeImbalanceModel
from ..config.logging import logger


class TradeCollector:
    """Trade 데이터 수집기"""
    
    def __init__(self):
        self.adapter = UpbitTradeAdapter()
        self.calculator = TradeImbalanceCalculator()
        self.running = False
        self._save_lock = asyncio.Lock()  # 동시 실행 방지 락
    
    async def start(self, symbols: List[str]) -> None:
        """수집 시작"""
        self.running = True
        logger.info("Trade 수집기 시작", symbols=symbols)
        
        # WebSocket 구독
        try:
            await self.adapter.subscribe(symbols, self._on_trade_data)
            logger.info("Trade WebSocket 구독 완료", symbols=symbols)
        except Exception as e:
            logger.error("Trade WebSocket 구독 실패", error=str(e), symbols=symbols)
            raise
        
        # 1초마다 집계 및 저장
        asyncio.create_task(self._aggregate_loop())
        logger.info("Trade 집계 루프 시작")
    
    async def stop(self) -> None:
        """수집 중지"""
        logger.info("Trade 수집기 중지")
        self.running = False
        await self.adapter.disconnect()
    
    async def _on_trade_data(self, data: Dict[str, Any]) -> None:
        """Trade 데이터 수신 콜백"""
        self.calculator.add_trade(data)
        # 너무 자주 로그를 찍지 않도록 주기적으로만 로그
        symbol = data.get("code")
        if symbol:
            logger.debug("Trade 데이터 수신", symbol=symbol)
    
    async def _aggregate_loop(self) -> None:
        """1초마다 집계 및 저장"""
        save_count = 0
        while self.running:
            try:
                await asyncio.sleep(1)
                saved = await self._save_imbalances()
                if saved:
                    save_count += 1
                    if save_count % 10 == 0:  # 10초마다 로그
                        logger.info("Trade 데이터 저장 중", save_count=save_count)
            except Exception as e:
                logger.error("Trade 집계 오류", error=str(e), error_type=type(e).__name__, exc_info=True)
    
    async def _save_imbalances(self) -> bool:
        """체결 방향 비율 저장
        
        Returns:
            bool: 저장 성공 여부
        """
        # 동시 실행 방지: 락을 획득한 후에만 저장 로직 실행
        async with self._save_lock:
            async with AsyncSessionLocal() as session:
                try:
                    from sqlalchemy import select
                    from ..infrastructure.persistence.database.models import MonitoredSymbolsModel
                    
                    # 모니터링 중인 종목 목록 가져오기
                    result = await session.execute(
                        select(MonitoredSymbolsModel).where(
                            MonitoredSymbolsModel.is_active == True
                        )
                    )
                    symbols = [row.symbol for row in result.scalars().all()]
                    
                    saved_count = 0
                    skipped_count = 0
                    current_time = datetime.utcnow()
                    # 최근 1초 이내 중복 체크를 위한 cutoff_time
                    cutoff_time = current_time - timedelta(seconds=1)
                    
                    # 각 종목, 각 윈도우(30s, 60s)에 대해 저장
                    for symbol in symbols:
                        for window_seconds in [30, 60]:
                            imbalance_data = self.calculator.calculate(symbol, window_seconds)
                            if imbalance_data:
                                # window_seconds를 초 단위로 저장 (30초 → 30, 60초 → 60)
                                window_seconds_value = window_seconds
                                
                                # 중복 체크: 최근 1초 이내 같은 계산 결과가 있는지 확인
                                existing_result = await session.execute(
                                    select(MetricsTradeImbalanceModel).where(
                                        MetricsTradeImbalanceModel.symbol == symbol,
                                        MetricsTradeImbalanceModel.window_seconds == window_seconds_value,
                                        MetricsTradeImbalanceModel.timestamp >= cutoff_time,
                                        MetricsTradeImbalanceModel.buy_volume == imbalance_data["buy_volume"],
                                        MetricsTradeImbalanceModel.sell_volume == imbalance_data["sell_volume"],
                                        MetricsTradeImbalanceModel.ti == imbalance_data["ti"],
                                        MetricsTradeImbalanceModel.cvd == imbalance_data["cvd"]
                                    )
                                )
                                if existing_result.scalar_one_or_none():
                                    skipped_count += 1
                                    continue  # 이미 존재하면 스킵
                                
                                imbalance_model = MetricsTradeImbalanceModel(
                                    symbol=symbol,
                                    timestamp=current_time,
                                    window_seconds=window_seconds_value,  # 초 단위로 저장 (30초 → 30, 60초 → 60)
                                    buy_volume=imbalance_data["buy_volume"],
                                    sell_volume=imbalance_data["sell_volume"],
                                    ti=imbalance_data["ti"],
                                    cvd=imbalance_data["cvd"],
                                )
                                session.add(imbalance_model)
                                saved_count += 1
                    
                    if saved_count > 0:
                        await session.commit()
                        logger.debug(
                            "Trade 데이터 저장 완료",
                            saved_count=saved_count,
                            skipped_count=skipped_count
                        )
                        return True
                    if skipped_count > 0:
                        logger.debug(
                            "Trade 데이터 중복으로 스킵",
                            skipped_count=skipped_count
                        )
                    return False
                except Exception as e:
                    await session.rollback()
                    logger.error("Trade 저장 오류", error=str(e), error_type=type(e).__name__, exc_info=True)
                    return False

