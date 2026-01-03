"""
단기 변동성 평가지표 계산 서비스
"""
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import math


class VolatilityCalculator:
    """단기 변동성 평가지표 계산기"""
    
    def __init__(self):
        # 캔들 데이터 저장 (symbol별)
        self.candles: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.max_candles = 30  # 최대 30개 캔들 저장 (30분)
    
    def add_candle(self, candle_data: Dict[str, Any]) -> None:
        """
        캔들 데이터 추가
        
        Args:
            candle_data: 업비트 candle 데이터
        """
        try:
            symbol = candle_data.get("code")
            if not symbol:
                return
            
            candle_date_time_kst = candle_data.get("candle_date_time_kst")
            if not candle_date_time_kst:
                return
            
            # 캔들 데이터 저장
            candle = {
                "timestamp": datetime.fromisoformat(candle_date_time_kst.replace("Z", "+00:00")),
                "open": Decimal(str(candle_data.get("opening_price", 0))),
                "high": Decimal(str(candle_data.get("high_price", 0))),
                "low": Decimal(str(candle_data.get("low_price", 0))),
                "close": Decimal(str(candle_data.get("trade_price", 0))),
            }
            
            candles_list = self.candles[symbol]
            
            # 같은 타임스탬프의 캔들이 있으면 업데이트, 없으면 추가
            existing_index = None
            for i, existing in enumerate(candles_list):
                if existing["timestamp"] == candle["timestamp"]:
                    existing_index = i
                    break
            
            if existing_index is not None:
                candles_list[existing_index] = candle
            else:
                candles_list.append(candle)
                # 최대 개수 제한
                if len(candles_list) > self.max_candles:
                    candles_list.pop(0)
            
            # 타임스탬프 순으로 정렬
            candles_list.sort(key=lambda x: x["timestamp"])
        except Exception:
            pass
    
    def calculate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        단기 변동성 계산
        
        Args:
            symbol: 종목 코드
            
        Returns:
            {
                "symbol": str,
                "volatility_15m": Decimal,
                "volatility_30m": Decimal,
                "range_1m": Decimal,
                "range_1m_mean_15m": Decimal
            } 또는 None
        """
        try:
            candles_list = self.candles.get(symbol, [])
            if len(candles_list) < 1:
                return None
            
            # 최신 캔들
            latest = candles_list[-1]
            
            # 1분 범위 계산
            if latest["open"] == 0:
                range_1m = Decimal("0")
            else:
                range_1m = (latest["high"] - latest["low"]) / latest["open"]
            
            # range_1m_mean_15m 계산 (최근 15개 캔들의 range_1m 평균)
            range_1m_mean_15m = None
            if len(candles_list) >= 15:
                recent_ranges = []
                for candle in candles_list[-15:]:
                    if candle["open"] > 0:
                        candle_range = (candle["high"] - candle["low"]) / candle["open"]
                        recent_ranges.append(candle_range)
                if recent_ranges:
                    range_1m_mean_15m = sum(recent_ranges) / Decimal(str(len(recent_ranges)))
            
            # 로그수익률 계산
            returns = []
            for i in range(1, len(candles_list)):
                prev_close = candles_list[i-1]["close"]
                curr_close = candles_list[i]["close"]
                
                if prev_close > 0 and curr_close > 0:
                    log_return = math.log(float(curr_close / prev_close))
                    returns.append(Decimal(str(log_return)))
            
            if len(returns) < 2:
                return {
                    "symbol": symbol,
                    "volatility_15m": None,
                    "volatility_30m": None,
                    "range_1m": range_1m,
                    "range_1m_mean_15m": range_1m_mean_15m,
                }
            
            # 15분 변동성 (최근 15개 캔들)
            returns_15m = returns[-15:] if len(returns) >= 15 else returns
            volatility_15m = self._calculate_std(returns_15m) if returns_15m else None
            
            # 30분 변동성 (최근 30개 캔들)
            returns_30m = returns[-30:] if len(returns) >= 30 else returns
            volatility_30m = self._calculate_std(returns_30m) if returns_30m else None
            
            return {
                "symbol": symbol,
                "volatility_15m": volatility_15m,
                "volatility_30m": volatility_30m,
                "range_1m": range_1m,
                "range_1m_mean_15m": range_1m_mean_15m,
            }
        except Exception:
            return None
    
    def _calculate_std(self, values: List[Decimal]) -> Optional[Decimal]:
        """표준편차 계산"""
        if not values or len(values) < 2:
            return None
        
        try:
            mean = sum(values) / Decimal(str(len(values)))
            variance = sum((v - mean) ** 2 for v in values) / Decimal(str(len(values) - 1))
            std = variance.sqrt()
            return std
        except Exception:
            return None


