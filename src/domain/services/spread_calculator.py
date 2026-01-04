"""
스프레드 평가지표 계산 서비스
"""
from decimal import Decimal
from typing import Dict, Any, Optional


class SpreadCalculator:
    """스프레드 평가지표 계산기"""
    
    @staticmethod
    def calculate(orderbook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        스프레드 계산
        
        Args:
            orderbook_data: 업비트 orderbook 데이터
            
        Returns:
            {
                "symbol": str,
                "spread_bps": Decimal,
                "mid_price": Decimal
            } 또는 None
        """
        try:
            symbol = orderbook_data.get("code")
            if not symbol:
                return None
            
            orderbook_units = orderbook_data.get("orderbook_units", [])
            if not orderbook_units or len(orderbook_units) == 0:
                return None
            
            # 최상위 호가
            ask0 = Decimal(str(orderbook_units[0].get("ask_price", 0)))
            bid0 = Decimal(str(orderbook_units[0].get("bid_price", 0)))
            
            if ask0 == 0 or bid0 == 0:
                return None
            
            # 중간가격
            mid = (ask0 + bid0) / Decimal("2")
            
            # 스프레드 (bps)
            spread = ask0 - bid0
            spread_bps = (spread / mid) * Decimal("10000")
            
            return {
                "symbol": symbol,
                "spread_bps": spread_bps,
                "mid_price": mid,
            }
        except Exception:
            return None




