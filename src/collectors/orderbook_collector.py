"""
Orderbook 데이터 수집기
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
from decimal import Decimal
import statistics
from typing import List

from ..infrastructure.adapters.orderbook import UpbitOrderbookAdapter
from ..domain.services.spread_calculator import SpreadCalculator
from ..domain.services.orderbook_imbalance_calculator import OrderbookImbalanceCalculator
from ..domain.services.slippage_calculator import SlippageCalculator
from ..infrastructure.persistence.database.session import AsyncSessionLocal
from ..infrastructure.persistence.database.models import (
    MetricsSpreadModel,
    MetricsOrderbookImbalanceModel,
    MetricsSlippageModel,
    OrderSide,
)
from ..config.logging import logger


def normalize_decimal(value: Optional[Decimal], min_value: Decimal = Decimal("0.0001")) -> Optional[Decimal]:
    """
    Decimal 값을 정규화하여 PostgreSQL NUMERIC 타입으로 저장 가능하도록 합니다.
    
    asyncpg가 인코딩할 수 없는 매우 작은 지수 값을 안전하게 처리합니다.
    """
    if value is None:
        return None
    
    try:
        # 먼저 정규화 시도
        normalized = value.normalize()
        
        # 0인 경우 바로 반환
        if normalized == 0:
            return Decimal("0")
        
        # 지수 확인
        sign, digits, exponent = normalized.as_tuple()
        
        # asyncpg가 인코딩할 수 없는 범위: 지수가 -100 미만이거나 너무 큰 경우
        # PostgreSQL NUMERIC은 최대 지수 범위가 있지만, asyncpg는 더 제한적
        if exponent < -100 or exponent > 100:
            # 지수가 너무 작거나 크면 0으로 처리
            return Decimal("0")
        
        # 의미 있는 작은 값은 보존 (min_value 이상)
        if abs(normalized) >= min_value:
            return normalized
        
        # min_value 미만의 값은 0으로 처리 (의미 없는 노이즈)
        return Decimal("0")
        
    except (ValueError, AttributeError, TypeError):
        # 정규화 실패 시 0으로 처리
        return Decimal("0")


class OrderbookCollector:
    """Orderbook 데이터 수집기"""
    
    def __init__(self):
        self.adapter = UpbitOrderbookAdapter()
        self.spread_calculator = SpreadCalculator()
        self.imbalance_calculator = OrderbookImbalanceCalculator()
        self.slippage_calculator = SlippageCalculator()
        
        # 1초 단위 버퍼 (symbol별)
        self.buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # 시계열 데이터 저장 (최근 60초)
        self.spread_series: Dict[str, List[float]] = defaultdict(list)  # spread_bps 시계열 (60개)
        self.imbalance_series: Dict[str, List[float]] = defaultdict(list)  # imbalance 시계열 (60개)
        self.slippage_series: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))  # side별 slippage 시계열 (60개)
        
        # EMA 계산을 위한 이전 값 저장
        self.spread_ema_10s: Dict[str, Optional[Decimal]] = {}  # symbol별 EMA 값
        self.imbalance_ema_5s: Dict[str, Optional[Decimal]] = {}  # symbol별 EMA 값
        self.imbalance_ema_30s: Dict[str, Optional[Decimal]] = {}  # symbol별 EMA 값
        self.slippage_ema_30s: Dict[str, Dict[str, Optional[Decimal]]] = defaultdict(lambda: defaultdict(lambda: None))  # symbol, side별 EMA 값
        
        self.running = False
    
    async def start(self, symbols: List[str]) -> None:
        """수집 시작"""
        self.running = True
        logger.info("Orderbook 수집기 시작", symbols=symbols)
        
        # WebSocket 구독
        try:
            await self.adapter.subscribe(symbols, self._on_orderbook_data)
            logger.info("Orderbook WebSocket 구독 완료", symbols=symbols)
        except Exception as e:
            logger.error("Orderbook WebSocket 구독 실패", error=str(e), symbols=symbols)
            raise
        
        # 1초마다 집계 및 저장
        asyncio.create_task(self._aggregate_loop())
        logger.info("Orderbook 집계 루프 시작")
    
    async def stop(self) -> None:
        """수집 중지"""
        logger.info("Orderbook 수집기 중지")
        self.running = False
        await self.adapter.disconnect()
    
    async def _on_orderbook_data(self, data: Dict[str, Any]) -> None:
        """Orderbook 데이터 수신 콜백"""
        symbol = data.get("code")
        if symbol:
            self.buffer[symbol].append(data)
            # 너무 자주 로그를 찍지 않도록 주기적으로만 로그
            if len(self.buffer[symbol]) % 100 == 0:
                logger.debug("Orderbook 데이터 수신", symbol=symbol, buffer_size=len(self.buffer[symbol]))
    
    async def _aggregate_loop(self) -> None:
        """1초마다 집계 및 저장"""
        save_count = 0
        while self.running:
            try:
                await asyncio.sleep(1)
                saved = await self._aggregate_and_save()
                if saved:
                    save_count += 1
                    if save_count % 10 == 0:  # 10초마다 로그
                        logger.info("Orderbook 데이터 저장 중", save_count=save_count)
            except Exception as e:
                logger.error("Orderbook 집계 오류", error=str(e), error_type=type(e).__name__, exc_info=True)
    
    async def _aggregate_and_save(self) -> bool:
        """버퍼 데이터 집계 및 저장
        
        Returns:
            bool: 저장 성공 여부
        """
        async with AsyncSessionLocal() as session:
            try:
                saved_count = 0
                for symbol, data_list in list(self.buffer.items()):
                    if not data_list:
                        continue
                    
                    # 1초 동안 수신된 데이터의 median 계산
                    # 스프레드 계산
                    spread_values = []
                    mid_prices = []
                    
                    for data in data_list:
                        result = self.spread_calculator.calculate(data)
                        if result:
                            spread_values.append(float(result["spread_bps"]))
                            mid_prices.append(float(result["mid_price"]))
                    
                    if spread_values:
                        # 1초 내 median 계산
                        median_spread_1s = Decimal(str(statistics.median(spread_values)))
                        median_mid = Decimal(str(statistics.median(mid_prices)))
                        
                        # 시계열에 추가 (최근 60개 유지)
                        self.spread_series[symbol].append(float(median_spread_1s))
                        if len(self.spread_series[symbol]) > 60:
                            self.spread_series[symbol].pop(0)
                        
                        # last, median_1s, p95_60s 계산
                        last_spread = Decimal(str(self.spread_series[symbol][-1])) if self.spread_series[symbol] else median_spread_1s
                        median_1s = median_spread_1s
                        
                        # EMA 10초 계산
                        alpha_10s = Decimal("2") / Decimal("11")  # 10초 EMA alpha
                        if symbol not in self.spread_ema_10s:
                            self.spread_ema_10s[symbol] = normalize_decimal(median_spread_1s)
                        else:
                            new_ema = alpha_10s * median_spread_1s + (Decimal("1") - alpha_10s) * self.spread_ema_10s[symbol]
                            self.spread_ema_10s[symbol] = normalize_decimal(new_ema)
                        ema_10s = self.spread_ema_10s[symbol]
                        
                        # p95_60s 계산 (최근 60초 데이터)
                        p95_60s = None
                        if len(self.spread_series[symbol]) >= 60:
                            sorted_values = sorted(self.spread_series[symbol])
                            p95_index = int(len(sorted_values) * 0.95)
                            p95_60s = Decimal(str(sorted_values[p95_index]))
                        
                        # 스프레드 저장
                        spread_model = MetricsSpreadModel(
                            symbol=symbol,
                            timestamp=datetime.utcnow(),
                            spread_bps=normalize_decimal(last_spread),  # last 값
                            mid_price=normalize_decimal(median_mid),
                            spread_bps_ema_10s=normalize_decimal(ema_10s),  # EMA 10초
                            spread_bps_mean_60s=normalize_decimal(median_1s),  # median_1s (1초 내 중앙값)
                            spread_bps_p95_5m=normalize_decimal(p95_60s) if p95_60s else None,  # p95_60s
                        )
                        session.add(spread_model)
                    
                    # 오더북 불균형 계산
                    imbalance_values = []
                    bid_volumes = []
                    ask_volumes = []
                    
                    for data in data_list:
                        result = self.imbalance_calculator.calculate(data)
                        if result:
                            imbalance_values.append(float(result["imbalance"]))
                            bid_volumes.append(float(result["bid_volume"]))
                            ask_volumes.append(float(result["ask_volume"]))
                    
                    if imbalance_values:
                        # 1초 내 median 계산
                        median_imbalance_1s = Decimal(str(statistics.median(imbalance_values)))
                        median_bid_volume = Decimal(str(statistics.median(bid_volumes)))
                        median_ask_volume = Decimal(str(statistics.median(ask_volumes)))
                        
                        # 시계열에 추가 (최근 60개 유지)
                        self.imbalance_series[symbol].append(float(median_imbalance_1s))
                        if len(self.imbalance_series[symbol]) > 60:
                            self.imbalance_series[symbol].pop(0)
                        
                        # last, median_1s, mean_10s, mean_60s 계산
                        last_imbalance = Decimal(str(self.imbalance_series[symbol][-1])) if self.imbalance_series[symbol] else median_imbalance_1s
                        median_1s = median_imbalance_1s
                        
                        # EMA 5초, 30초 계산
                        alpha_5s = Decimal("2") / Decimal("6")  # 5초 EMA alpha
                        alpha_30s = Decimal("2") / Decimal("31")  # 30초 EMA alpha
                        
                        if symbol not in self.imbalance_ema_5s:
                            self.imbalance_ema_5s[symbol] = normalize_decimal(median_imbalance_1s)
                        else:
                            new_ema_5s = alpha_5s * median_imbalance_1s + (Decimal("1") - alpha_5s) * self.imbalance_ema_5s[symbol]
                            self.imbalance_ema_5s[symbol] = normalize_decimal(new_ema_5s)
                        
                        if symbol not in self.imbalance_ema_30s:
                            self.imbalance_ema_30s[symbol] = normalize_decimal(median_imbalance_1s)
                        else:
                            new_ema_30s = alpha_30s * median_imbalance_1s + (Decimal("1") - alpha_30s) * self.imbalance_ema_30s[symbol]
                            self.imbalance_ema_30s[symbol] = normalize_decimal(new_ema_30s)
                        
                        # mean_10s, mean_60s 계산
                        mean_10s = None
                        mean_60s = None
                        if len(self.imbalance_series[symbol]) >= 10:
                            mean_10s = Decimal(str(statistics.mean(self.imbalance_series[symbol][-10:])))
                        if len(self.imbalance_series[symbol]) >= 60:
                            mean_60s = Decimal(str(statistics.mean(self.imbalance_series[symbol][-60:])))
                        
                        # 오더북 불균형 저장
                        imbalance_model = MetricsOrderbookImbalanceModel(
                            symbol=symbol,
                            timestamp=datetime.utcnow(),
                            imbalance=normalize_decimal(last_imbalance),  # last
                            bid_volume=normalize_decimal(median_bid_volume),
                            ask_volume=normalize_decimal(median_ask_volume),
                            imbalance_ema_5s=normalize_decimal(self.imbalance_ema_5s[symbol]),  # EMA 5초
                            imbalance_ema_30s=normalize_decimal(self.imbalance_ema_30s[symbol]),  # EMA 30초
                            imbalance_mean_5m=normalize_decimal(mean_10s) if mean_10s else None,  # mean_10s (컬럼명은 5m이지만 실제로는 10s)
                            imbalance_zscore_24h=normalize_decimal(mean_60s) if mean_60s else None,  # mean_60s (컬럼명은 24h지만 실제로는 60s)
                        )
                        session.add(imbalance_model)
                    
                    # 슬리피지 계산 (매수/매도)
                    for side in ["BUY", "SELL"]:
                        slippage_values = []
                        
                        for data in data_list:
                            result = self.slippage_calculator.calculate(data, side)
                            if result:
                                slippage_values.append(float(result["slippage_bps"]))
                        
                        if slippage_values:
                            # 1초 내 last 값 (최신 값)
                            last_slippage = Decimal(str(slippage_values[-1]))
                            
                            # 시계열에 추가 (최근 60개 유지)
                            self.slippage_series[symbol][side].append(float(last_slippage))
                            if len(self.slippage_series[symbol][side]) > 60:
                                self.slippage_series[symbol][side].pop(0)
                            
                            # EMA 30초 계산
                            alpha_30s = Decimal("2") / Decimal("31")  # 30초 EMA alpha
                            if self.slippage_ema_30s[symbol][side] is None:
                                self.slippage_ema_30s[symbol][side] = normalize_decimal(last_slippage)
                            else:
                                new_ema = alpha_30s * last_slippage + (Decimal("1") - alpha_30s) * self.slippage_ema_30s[symbol][side]
                                self.slippage_ema_30s[symbol][side] = normalize_decimal(new_ema)
                            
                            # mean_10s, p95_60s 계산
                            mean_10s = None
                            p95_60s = None
                            
                            if len(self.slippage_series[symbol][side]) >= 10:
                                mean_10s = Decimal(str(statistics.mean(self.slippage_series[symbol][side][-10:])))
                            
                            if len(self.slippage_series[symbol][side]) >= 60:
                                sorted_values = sorted(self.slippage_series[symbol][side])
                                p95_index = int(len(sorted_values) * 0.95)
                                p95_60s = Decimal(str(sorted_values[p95_index]))
                            
                            # 슬리피지 저장
                            slippage_model = MetricsSlippageModel(
                                symbol=symbol,
                                timestamp=datetime.utcnow(),
                                order_size_krw=Decimal(str(self.slippage_calculator.standard_order_size_krw)),
                                side=OrderSide.BUY if side == "BUY" else OrderSide.SELL,
                                slippage_bps=normalize_decimal(last_slippage),  # last
                                slippage_bps_ema_30s=normalize_decimal(self.slippage_ema_30s[symbol][side]),  # EMA 30초
                                slippage_bps_mean_5m=normalize_decimal(p95_60s),  # p95_60s (컬럼명은 5m이지만 실제로는 p95_60s)
                            )
                            session.add(slippage_model)
                    
                    # 버퍼 비우기
                    self.buffer[symbol] = []
                    saved_count += 1
                
                if saved_count > 0:
                    await session.commit()
                    logger.debug("Orderbook 데이터 저장 완료", saved_symbols=saved_count)
                    return True
                return False
            except Exception as e:
                await session.rollback()
                logger.error("Orderbook 저장 오류", error=str(e), error_type=type(e).__name__, exc_info=True)
                return False


