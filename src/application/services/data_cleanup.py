"""
데이터 정리 서비스
12시간 이상 된 metrics 데이터를 삭제합니다.
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from ...infrastructure.persistence.database.session import AsyncSessionLocal
from ...infrastructure.persistence.database.models import (
    MetricsSpreadModel,
    MetricsOrderbookImbalanceModel,
    MetricsSlippageModel,
    MetricsTradeImbalanceModel,
    MetricsVolatilityModel,
    MetricsLiquidityModel,
)
from ...config.logging import logger


async def cleanup_old_data() -> None:
    """
    12시간 이상 된 모든 metrics 데이터를 삭제합니다.
    
    삭제 대상 테이블:
    - metrics_spread
    - metrics_orderbook_imbalance
    - metrics_slippage
    - metrics_trade_imbalance
    - metrics_volatility
    - metrics_liquidity
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=12)
    
    logger.info("데이터 정리 작업 시작", cutoff_time=cutoff_time.isoformat())
    
    async with AsyncSessionLocal() as session:
        try:
            total_deleted = 0
            
            # 각 테이블별로 삭제
            models = [
                (MetricsSpreadModel, "metrics_spread"),
                (MetricsOrderbookImbalanceModel, "metrics_orderbook_imbalance"),
                (MetricsSlippageModel, "metrics_slippage"),
                (MetricsTradeImbalanceModel, "metrics_trade_imbalance"),
                (MetricsVolatilityModel, "metrics_volatility"),
                (MetricsLiquidityModel, "metrics_liquidity"),
            ]
            
            for model, table_name in models:
                try:
                    result = await session.execute(
                        delete(model).where(model.timestamp < cutoff_time)
                    )
                    deleted_count = result.rowcount
                    total_deleted += deleted_count
                    
                    if deleted_count > 0:
                        logger.info(
                            "데이터 삭제 완료",
                            table=table_name,
                            deleted_count=deleted_count,
                            cutoff_time=cutoff_time.isoformat(),
                        )
                    else:
                        logger.debug(
                            "삭제할 데이터 없음",
                            table=table_name,
                            cutoff_time=cutoff_time.isoformat(),
                        )
                except Exception as e:
                    logger.error(
                        "데이터 삭제 오류",
                        table=table_name,
                        error=str(e),
                        error_type=type(e).__name__,
                        exc_info=True,
                    )
            
            await session.commit()
            logger.info(
                "데이터 정리 작업 완료",
                total_deleted=total_deleted,
                cutoff_time=cutoff_time.isoformat(),
            )
            
        except Exception as e:
            await session.rollback()
            logger.error(
                "데이터 정리 작업 실패",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

