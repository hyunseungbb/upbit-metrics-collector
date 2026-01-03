"""
체결 방향 비율 평가지표 계산 서비스
"""
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class TradeImbalanceCalculator:
    """체결 방향 비율 평가지표 계산기"""
    
    def __init__(self):
        # 롤링 윈도우 데이터 저장 (symbol별, window별)
        # window는 초 단위로 저장 (10, 30, 60초)
        self.windows: Dict[str, Dict[int, List[Dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.window_sizes = [10, 30, 60]  # 10초, 30초, 60초
    
    def add_trade(self, trade_data: Dict[str, Any]) -> None:
        """
        체결 데이터 추가
        
        Args:
            trade_data: 업비트 trade 데이터
        """
        try:
            symbol = trade_data.get("code")
            if not symbol:
                return
            
            ask_bid = trade_data.get("ask_bid")  # "ASK" 또는 "BID"
            trade_volume = Decimal(str(trade_data.get("trade_volume", 0)))
            trade_timestamp = trade_data.get("trade_timestamp_ms", 0)
            
            if not ask_bid or trade_volume == 0:
                return
            
            # 타임스탬프를 datetime으로 변환
            trade_time = datetime.fromtimestamp(trade_timestamp / 1000)
            
            # 각 윈도우에 추가 (초 단위)
            for window_seconds in self.window_sizes:
                window_data = self.windows[symbol][window_seconds]
                
                # 윈도우 범위 밖의 데이터 제거
                cutoff_time = trade_time - timedelta(seconds=window_seconds)
                window_data[:] = [
                    item for item in window_data
                    if item["timestamp"] > cutoff_time
                ]
                
                # 새 데이터 추가
                window_data.append({
                    "timestamp": trade_time,
                    "ask_bid": ask_bid,
                    "volume": trade_volume,
                })
        except Exception:
            pass
    
    def calculate(self, symbol: str, window_seconds: int) -> Optional[Dict[str, Any]]:
        """
        체결 방향 비율 계산
        
        Args:
            symbol: 종목 코드
            window_seconds: 윈도우 크기 (초)
            
        Returns:
            {
                "symbol": str,
                "window_seconds": int,
                "buy_volume": Decimal,
                "sell_volume": Decimal,
                "ti": Decimal (0~1),
                "cvd": Decimal
            } 또는 None
        """
        try:
            window_data = self.windows[symbol].get(window_seconds, [])
            if not window_data:
                return None
            
            buy_volume = Decimal("0")
            sell_volume = Decimal("0")
            
            for item in window_data:
                if item["ask_bid"] == "BID":
                    buy_volume += item["volume"]
                else:  # "ASK"
                    sell_volume += item["volume"]
            
            total_volume = buy_volume + sell_volume
            if total_volume == 0:
                return None
            
            # Trade Imbalance (0~1)
            ti = buy_volume / total_volume
            
            # Cumulative Volume Delta
            cvd = buy_volume - sell_volume
            
            return {
                "symbol": symbol,
                "window_seconds": window_seconds,
                "buy_volume": buy_volume,
                "sell_volume": sell_volume,
                "ti": ti,
                "cvd": cvd,
            }
        except Exception:
            return None
    
    def calculate_all_windows(self, symbol: str) -> Dict[int, Optional[Dict[str, Any]]]:
        """
        모든 윈도우에 대해 계산
        
        Returns:
            {window_seconds: result_dict}
        """
        results = {}
        for window_seconds in self.window_sizes:
            results[window_seconds] = self.calculate(symbol, window_seconds)
        return results


