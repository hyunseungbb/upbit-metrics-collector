"""
오더북 불균형 평가지표 계산 서비스
"""
from decimal import Decimal
from typing import Dict, Any, Optional
from src.config.env_config import ORDERBOOK_LEVELS


class OrderbookImbalanceCalculator:
    """오더북 불균형 평가지표 계산기"""
    
    def __init__(self, levels: int = ORDERBOOK_LEVELS):
        """
        Args:
            levels: 계산에 사용할 호가 레벨 수 (기본값: 15)
        """
        self.levels = levels
    
    def calculate(self, orderbook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        오더북 불균형 계산
        
        Args:
            orderbook_data: 업비트 orderbook 데이터
            
        Returns:
            {
                "symbol": str,
                "imbalance": Decimal (0~1),
                "bid_volume": Decimal,
                "ask_volume": Decimal
            } 또는 None
        """
        try:
            symbol = orderbook_data.get("code")
            if not symbol:
                return None
            
            orderbook_units = orderbook_data.get("orderbook_units", [])
            if not orderbook_units:
                return None
            
            # 상위 N레벨 누적
            bid_volume = Decimal("0")
            ask_volume = Decimal("0")
            
            for i, unit in enumerate(orderbook_units[:self.levels]):
                bid_price = Decimal(str(unit.get("bid_price", 0)))
                bid_size = Decimal(str(unit.get("bid_size", 0)))
                ask_price = Decimal(str(unit.get("ask_price", 0)))
                ask_size = Decimal(str(unit.get("ask_size", 0)))
                
                # 가중치 적용 (가까운 호가일수록 높은 가중치)
                weight = Decimal(str(self.levels - i)) / Decimal(str(self.levels))
                
                bid_volume += bid_size * weight
                ask_volume += ask_size * weight
            
            total_volume = bid_volume + ask_volume
            if total_volume == 0:
                return None
            
            # 불균형 계산 (0~1)
            imbalance = bid_volume / total_volume
            
            return {
                "symbol": symbol,
                "imbalance": imbalance,
                "bid_volume": bid_volume,
                "ask_volume": ask_volume,
            }
        except Exception:
            return None




