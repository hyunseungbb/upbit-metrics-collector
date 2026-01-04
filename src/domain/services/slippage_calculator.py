"""
예상 슬리피지 평가지표 계산 서비스
"""
from decimal import Decimal
from typing import Dict, Any, Optional, Literal
from src.config.env_config import STANDARD_ORDER_SIZE_KRW


class SlippageCalculator:
    """예상 슬리피지 평가지표 계산기"""
    
    def __init__(self, standard_order_size_krw: float = STANDARD_ORDER_SIZE_KRW):
        """
        Args:
            standard_order_size_krw: 표준 주문 크기 (KRW)
        """
        self.standard_order_size_krw = Decimal(str(standard_order_size_krw))
    
    def calculate(
        self, 
        orderbook_data: Dict[str, Any], 
        side: Literal["BUY", "SELL"]
    ) -> Optional[Dict[str, Any]]:
        """
        예상 슬리피지 계산
        
        Args:
            orderbook_data: 업비트 orderbook 데이터
            side: 주문 방향 (BUY: 매수, SELL: 매도)
            
        Returns:
            {
                "symbol": str,
                "order_size_krw": Decimal,
                "side": str,
                "slippage_bps": Decimal,
                "vwap": Decimal
            } 또는 None
        """
        try:
            symbol = orderbook_data.get("code")
            if not symbol:
                return None
            
            orderbook_units = orderbook_data.get("orderbook_units", [])
            if not orderbook_units:
                return None
            
            if side == "BUY":
                # 매수: ask 레벨 사용
                remaining_size = self.standard_order_size_krw
                total_cost = Decimal("0")
                total_quantity = Decimal("0")
                
                for unit in orderbook_units:
                    ask_price = Decimal(str(unit.get("ask_price", 0)))
                    ask_size = Decimal(str(unit.get("ask_size", 0)))
                    
                    if ask_price == 0 or ask_size == 0:
                        continue
                    
                    # 이 레벨에서 소화할 수 있는 수량
                    level_cost = ask_price * ask_size
                    
                    if level_cost <= remaining_size:
                        # 전체 레벨 소화
                        total_cost += level_cost
                        total_quantity += ask_size
                        remaining_size -= level_cost
                    else:
                        # 일부만 소화
                        quantity = remaining_size / ask_price
                        total_cost += remaining_size
                        total_quantity += quantity
                        remaining_size = Decimal("0")
                        break
                
                if total_quantity == 0:
                    return None
                
                vwap = total_cost / total_quantity
                ask0 = Decimal(str(orderbook_units[0].get("ask_price", 0)))
                
                if ask0 == 0:
                    return None
                
                slippage_bps = ((vwap - ask0) / ask0) * Decimal("10000")
                
            else:  # SELL
                # 매도: bid 레벨 사용
                remaining_size = self.standard_order_size_krw
                total_cost = Decimal("0")
                total_quantity = Decimal("0")
                
                for unit in orderbook_units:
                    bid_price = Decimal(str(unit.get("bid_price", 0)))
                    bid_size = Decimal(str(unit.get("bid_size", 0)))
                    
                    if bid_price == 0 or bid_size == 0:
                        continue
                    
                    # 이 레벨에서 소화할 수 있는 수량
                    level_cost = bid_price * bid_size
                    
                    if level_cost <= remaining_size:
                        # 전체 레벨 소화
                        total_cost += level_cost
                        total_quantity += bid_size
                        remaining_size -= level_cost
                    else:
                        # 일부만 소화
                        quantity = remaining_size / bid_price
                        total_cost += remaining_size
                        total_quantity += quantity
                        remaining_size = Decimal("0")
                        break
                
                if total_quantity == 0:
                    return None
                
                vwap = total_cost / total_quantity
                bid0 = Decimal(str(orderbook_units[0].get("bid_price", 0)))
                
                if bid0 == 0:
                    return None
                
                slippage_bps = ((bid0 - vwap) / bid0) * Decimal("10000")
            
            return {
                "symbol": symbol,
                "order_size_krw": self.standard_order_size_krw,
                "side": side,
                "slippage_bps": slippage_bps,
                "vwap": vwap,
            }
        except Exception:
            return None




