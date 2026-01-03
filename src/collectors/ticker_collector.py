"""
Ticker 데이터 수집기
"""
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal

from ..infrastructure.adapters.ticker import UpbitTickerAdapter
from ..infrastructure.persistence.database.session import AsyncSessionLocal
from ..infrastructure.persistence.database.models import MetricsLiquidityModel
from ..config.logging import logger


class TickerCollector:
    """Ticker 데이터 수집기"""
    
    def __init__(self):
        self.adapter = UpbitTickerAdapter()
        self.running = False
        self.ticker_buffer: Dict[str, Dict[str, Any]] = {}
    
    async def start(self, symbols: List[str]) -> None:
        """수집 시작"""
        self.running = True
        logger.info("Ticker 수집기 시작", symbols=symbols)
        
        # WebSocket 구독
        try:
            await self.adapter.subscribe(symbols, self._on_ticker_data)
            logger.info("Ticker WebSocket 구독 완료", symbols=symbols)
        except Exception as e:
            logger.error("Ticker WebSocket 구독 실패", error=str(e), symbols=symbols)
            raise
        
        # 30~60초마다 저장 (너무 자주 저장할 필요 없음)
        asyncio.create_task(self._save_loop())
        logger.info("Ticker 저장 루프 시작")
    
    async def stop(self) -> None:
        """수집 중지"""
        logger.info("Ticker 수집기 중지")
        self.running = False
        await self.adapter.disconnect()
    
    async def _on_ticker_data(self, data: Dict[str, Any]) -> None:
        """Ticker 데이터 수신 콜백"""
        symbol = data.get("code")
        if symbol:
            self.ticker_buffer[symbol] = data
            logger.debug("Ticker 데이터 수신", symbol=symbol)
    
    async def _save_loop(self) -> None:
        """30~60초마다 저장 (랜덤하게 30~60초 사이)"""
        import random
        save_count = 0
        while self.running:
            try:
                # 30~60초 사이 랜덤 대기
                wait_time = random.randint(30, 60)
                await asyncio.sleep(wait_time)
                saved_symbols = []
                for symbol, data in list(self.ticker_buffer.items()):
                    acc_trade_price_24h = Decimal(str(data.get("acc_trade_price_24h", 0)))
                    if acc_trade_price_24h > 0:
                        await self._save_liquidity(symbol, acc_trade_price_24h)
                        saved_symbols.append(symbol)
                if saved_symbols:
                    save_count += 1
                    logger.info("Ticker 데이터 저장 완료", saved_symbols=saved_symbols, save_count=save_count, wait_time=wait_time)
                self.ticker_buffer.clear()
            except Exception as e:
                logger.error("Ticker 저장 오류", error=str(e), error_type=type(e).__name__, exc_info=True)
    
    async def _save_liquidity(self, symbol: str, acc_trade_price_24h: Decimal) -> None:
        """유동성 저장"""
        async with AsyncSessionLocal() as session:
            try:
                liquidity_model = MetricsLiquidityModel(
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    acc_trade_price_24h=acc_trade_price_24h,
                )
                session.add(liquidity_model)
                await session.commit()
                logger.debug("유동성 저장 완료", symbol=symbol, acc_trade_price_24h=float(acc_trade_price_24h))
            except Exception as e:
                await session.rollback()
                logger.error("유동성 저장 오류", error=str(e), symbol=symbol, error_type=type(e).__name__, exc_info=True)

