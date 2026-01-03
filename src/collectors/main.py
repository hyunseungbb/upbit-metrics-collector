"""
메인 수집기 - 모든 수집기 통합 관리
"""
import asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from .orderbook_collector import OrderbookCollector
from .trade_collector import TradeCollector
from .candle_collector import CandleCollector
from .ticker_collector import TickerCollector
from ..infrastructure.persistence.database.session import AsyncSessionLocal
from ..infrastructure.persistence.database.models import MonitoredSymbolsModel
from ..application.services.data_cleanup import cleanup_old_data
from ..config.logging import logger


class MetricsCollector:
    """평가지표 수집기 (통합)"""
    
    def __init__(self):
        self.orderbook_collector = OrderbookCollector()
        self.trade_collector = TradeCollector()
        self.candle_collector = CandleCollector(unit=1)  # 1분봉
        self.ticker_collector = TickerCollector()
        self.running = False
    
    async def start(self) -> None:
        """수집 시작"""
        self.running = True
        
        # 모니터링 중인 종목 목록 가져오기
        symbols = await self._get_monitored_symbols()
        
        if not symbols:
            logger.warning("모니터링 중인 종목이 없습니다")
            return
        
        logger.info("수집 시작", symbol_count=len(symbols), symbols=symbols)
        
        # 모든 수집기 시작
        try:
            await self.orderbook_collector.start(symbols)
            logger.info("Orderbook 수집기 시작 완료")
        except Exception as e:
            logger.error("Orderbook 수집기 시작 실패", error=str(e))
        
        try:
            await self.trade_collector.start(symbols)
            logger.info("Trade 수집기 시작 완료")
        except Exception as e:
            logger.error("Trade 수집기 시작 실패", error=str(e))
        
        try:
            await self.candle_collector.start(symbols)
            logger.info("Candle 수집기 시작 완료")
        except Exception as e:
            logger.error("Candle 수집기 시작 실패", error=str(e))
        
        try:
            await self.ticker_collector.start(symbols)
            logger.info("Ticker 수집기 시작 완료")
        except Exception as e:
            logger.error("Ticker 수집기 시작 실패", error=str(e))
        
        # WebSocket 구독 상태 모니터링 시작 (30초마다)
        asyncio.create_task(self._monitor_subscriptions())
        logger.info("WebSocket 구독 상태 모니터링 시작")
        
        # 데이터 정리 스케줄러 시작 (6시간마다)
        asyncio.create_task(self._cleanup_scheduler())
        logger.info("데이터 정리 스케줄러 시작")
    
    async def stop(self) -> None:
        """수집 중지"""
        logger.info("수집 중지 시작")
        self.running = False
        await self.orderbook_collector.stop()
        await self.trade_collector.stop()
        await self.candle_collector.stop()
        await self.ticker_collector.stop()
        logger.info("수집 중지 완료")
    
    async def _get_monitored_symbols(self) -> List[str]:
        """모니터링 중인 종목 목록 가져오기"""
        async with AsyncSessionLocal() as session:
            try:
                from sqlalchemy import select
                result = await session.execute(
                    select(MonitoredSymbolsModel).where(
                        MonitoredSymbolsModel.is_active == True
                    )
                )
                symbols = [row.symbol for row in result.scalars().all()]
                logger.info("모니터링 종목 목록 조회", symbol_count=len(symbols), symbols=symbols)
                return symbols
            except Exception as e:
                logger.error("종목 목록 조회 오류", error=str(e), error_type=type(e).__name__)
                return []
    
    async def _monitor_subscriptions(self) -> None:
        """WebSocket 구독 상태 모니터링 (30초마다)"""
        while self.running:
            try:
                await asyncio.sleep(30)  # 30초마다 체크 (10초에서 30초로 변경하여 rate limit 방지)
                
                # 각 어댑터의 구독 상태 확인 및 재구독
                symbols = await self._get_monitored_symbols()
                if not symbols:
                    continue
                
                # Orderbook
                try:
                    if not await self.orderbook_collector.adapter.ensure_subscribed():
                        logger.debug("Orderbook 구독 상태 확인 실패 (재연결 중일 수 있음)")
                except Exception as e:
                    logger.error("Orderbook 구독 상태 확인 오류", error=str(e))
                
                # Trade
                try:
                    if not await self.trade_collector.adapter.ensure_subscribed():
                        logger.debug("Trade 구독 상태 확인 실패 (재연결 중일 수 있음)")
                except Exception as e:
                    logger.error("Trade 구독 상태 확인 오류", error=str(e))
                
                # Candle
                try:
                    if not await self.candle_collector.adapter.ensure_subscribed():
                        logger.debug("Candle 구독 상태 확인 실패 (재연결 중일 수 있음)")
                except Exception as e:
                    logger.error("Candle 구독 상태 확인 오류", error=str(e))
                
                # Ticker
                try:
                    if not await self.ticker_collector.adapter.ensure_subscribed():
                        logger.debug("Ticker 구독 상태 확인 실패 (재연결 중일 수 있음)")
                except Exception as e:
                    logger.error("Ticker 구독 상태 확인 오류", error=str(e))
                
            except Exception as e:
                logger.error("구독 상태 모니터링 오류", error=str(e), error_type=type(e).__name__)
                await asyncio.sleep(30)
    
    async def _cleanup_scheduler(self) -> None:
        """6시간마다 데이터 정리 실행"""
        # 첫 실행은 시작 후 6시간 뒤
        await asyncio.sleep(6 * 60 * 60)  # 6시간 대기
        
        while self.running:
            try:
                await cleanup_old_data()
            except Exception as e:
                logger.error(
                    "데이터 정리 스케줄러 오류",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
            
            # 다음 실행까지 6시간 대기
            if self.running:
                await asyncio.sleep(6 * 60 * 60)  # 6시간


async def main():
    """메인 함수"""
    collector = MetricsCollector()
    try:
        await collector.start()
        # 무한 대기
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트 수신, 수집 중지 중...")
        await collector.stop()
    except Exception as e:
        logger.error("수집기 실행 오류", error=str(e), error_type=type(e).__name__, exc_info=True)
        await collector.stop()
        raise


if __name__ == "__main__":
    asyncio.run(main())


