"""Add column comments

Revision ID: 3ab9742a6143
Revises: 001
Create Date: 2026-01-03 21:53:27.161438

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3ab9742a6143'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # metrics_spread 테이블 컬럼 COMMENT
    op.execute("COMMENT ON COLUMN metrics_spread.id IS '고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN metrics_spread.symbol IS '종목 코드 (예: KRW-BTC)'")
    op.execute("COMMENT ON COLUMN metrics_spread.timestamp IS '데이터 수집 시각'")
    op.execute("COMMENT ON COLUMN metrics_spread.spread_bps IS '스프레드 (basis points, ask-bid 차이를 중간가격 대비 백분율로 표현)'")
    op.execute("COMMENT ON COLUMN metrics_spread.mid_price IS '중간가격 ((ask_price + bid_price) / 2)'")
    op.execute("COMMENT ON COLUMN metrics_spread.spread_bps_ema_10s IS '10초 지수이동평균 스프레드'")
    op.execute("COMMENT ON COLUMN metrics_spread.spread_bps_mean_60s IS '60초 평균 스프레드 (실제로는 1초 내 median)'")
    op.execute("COMMENT ON COLUMN metrics_spread.spread_bps_p95_5m IS '5분간 95퍼센타일 스프레드 (실제로는 60초 p95)'")
    op.execute("COMMENT ON COLUMN metrics_spread.created_at IS '레코드 생성 시각'")
    
    # metrics_orderbook_imbalance 테이블 컬럼 COMMENT
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.id IS '고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.symbol IS '종목 코드'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.timestamp IS '데이터 수집 시각'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance IS '오더북 불균형 (0~1, bid_volume / (bid_volume + ask_volume))'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.bid_volume IS '매수 호가 총량'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.ask_volume IS '매도 호가 총량'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance_ema_5s IS '5초 지수이동평균 불균형'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance_ema_30s IS '30초 지수이동평균 불균형'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance_mean_5m IS '5분 평균 불균형 (실제로는 10초 평균)'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance_zscore_24h IS '24시간 Z-score (실제로는 60초 평균)'")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.created_at IS '레코드 생성 시각'")
    
    # metrics_slippage 테이블 컬럼 COMMENT
    op.execute("COMMENT ON COLUMN metrics_slippage.id IS '고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN metrics_slippage.symbol IS '종목 코드'")
    op.execute("COMMENT ON COLUMN metrics_slippage.timestamp IS '데이터 수집 시각'")
    op.execute("COMMENT ON COLUMN metrics_slippage.order_size_krw IS '주문 크기 (KRW)'")
    op.execute("COMMENT ON COLUMN metrics_slippage.side IS '주문 방향 (BUY/SELL)'")
    op.execute("COMMENT ON COLUMN metrics_slippage.slippage_bps IS '예상 슬리피지 (basis points)'")
    op.execute("COMMENT ON COLUMN metrics_slippage.slippage_bps_ema_30s IS '30초 지수이동평균 슬리피지'")
    op.execute("COMMENT ON COLUMN metrics_slippage.slippage_bps_mean_5m IS '5분 평균 슬리피지 (실제로는 60초 p95)'")
    op.execute("COMMENT ON COLUMN metrics_slippage.created_at IS '레코드 생성 시각'")
    
    # metrics_trade_imbalance 테이블 컬럼 COMMENT
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.id IS '고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.symbol IS '종목 코드'")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.timestamp IS '데이터 수집 시각'")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.window_minutes IS '롤링 윈도우 크기 (분, 실제로는 30초/60초)'")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.buy_volume IS '매수 체결량'")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.sell_volume IS '매도 체결량'")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.ti IS 'Trade Imbalance (0~1, buy_volume / total_volume)'")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.cvd IS 'Cumulative Volume Delta (buy_volume - sell_volume)'")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.created_at IS '레코드 생성 시각'")
    
    # metrics_volatility 테이블 컬럼 COMMENT
    op.execute("COMMENT ON COLUMN metrics_volatility.id IS '고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN metrics_volatility.symbol IS '종목 코드'")
    op.execute("COMMENT ON COLUMN metrics_volatility.timestamp IS '데이터 수집 시각'")
    op.execute("COMMENT ON COLUMN metrics_volatility.volatility_15m IS '15분 변동성 (로그수익률의 표준편차)'")
    op.execute("COMMENT ON COLUMN metrics_volatility.volatility_30m IS '30분 변동성 (로그수익률의 표준편차)'")
    op.execute("COMMENT ON COLUMN metrics_volatility.range_1m IS '1분 범위 ((high - low) / open)'")
    op.execute("COMMENT ON COLUMN metrics_volatility.range_1m_mean_15m IS '최근 15개 캔들의 range_1m 평균'")
    op.execute("COMMENT ON COLUMN metrics_volatility.created_at IS '레코드 생성 시각'")
    
    # metrics_liquidity 테이블 컬럼 COMMENT
    op.execute("COMMENT ON COLUMN metrics_liquidity.id IS '고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN metrics_liquidity.symbol IS '종목 코드'")
    op.execute("COMMENT ON COLUMN metrics_liquidity.timestamp IS '데이터 수집 시각'")
    op.execute("COMMENT ON COLUMN metrics_liquidity.acc_trade_price_24h IS '24시간 누적 거래대금 (KRW)'")
    op.execute("COMMENT ON COLUMN metrics_liquidity.created_at IS '레코드 생성 시각'")
    
    # monitored_symbols 테이블 컬럼 COMMENT
    op.execute("COMMENT ON COLUMN monitored_symbols.id IS '고유 식별자 (UUID)'")
    op.execute("COMMENT ON COLUMN monitored_symbols.symbol IS '모니터링 종목 코드'")
    op.execute("COMMENT ON COLUMN monitored_symbols.is_active IS '활성화 여부'")
    op.execute("COMMENT ON COLUMN monitored_symbols.created_at IS '레코드 생성 시각'")
    op.execute("COMMENT ON COLUMN monitored_symbols.updated_at IS '레코드 수정 시각'")

def downgrade() -> None:
    # 모든 COMMENT 제거
    op.execute("COMMENT ON COLUMN metrics_spread.id IS NULL")
    op.execute("COMMENT ON COLUMN metrics_spread.symbol IS NULL")
    op.execute("COMMENT ON COLUMN metrics_spread.timestamp IS NULL")
    op.execute("COMMENT ON COLUMN metrics_spread.spread_bps IS NULL")
    op.execute("COMMENT ON COLUMN metrics_spread.mid_price IS NULL")
    op.execute("COMMENT ON COLUMN metrics_spread.spread_bps_ema_10s IS NULL")
    op.execute("COMMENT ON COLUMN metrics_spread.spread_bps_mean_60s IS NULL")
    op.execute("COMMENT ON COLUMN metrics_spread.spread_bps_p95_5m IS NULL")
    op.execute("COMMENT ON COLUMN metrics_spread.created_at IS NULL")
    
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.id IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.symbol IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.timestamp IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.bid_volume IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.ask_volume IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance_ema_5s IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance_ema_30s IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance_mean_5m IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.imbalance_zscore_24h IS NULL")
    op.execute("COMMENT ON COLUMN metrics_orderbook_imbalance.created_at IS NULL")
    
    op.execute("COMMENT ON COLUMN metrics_slippage.id IS NULL")
    op.execute("COMMENT ON COLUMN metrics_slippage.symbol IS NULL")
    op.execute("COMMENT ON COLUMN metrics_slippage.timestamp IS NULL")
    op.execute("COMMENT ON COLUMN metrics_slippage.order_size_krw IS NULL")
    op.execute("COMMENT ON COLUMN metrics_slippage.side IS NULL")
    op.execute("COMMENT ON COLUMN metrics_slippage.slippage_bps IS NULL")
    op.execute("COMMENT ON COLUMN metrics_slippage.slippage_bps_ema_30s IS NULL")
    op.execute("COMMENT ON COLUMN metrics_slippage.slippage_bps_mean_5m IS NULL")
    op.execute("COMMENT ON COLUMN metrics_slippage.created_at IS NULL")
    
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.id IS NULL")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.symbol IS NULL")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.timestamp IS NULL")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.window_minutes IS NULL")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.buy_volume IS NULL")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.sell_volume IS NULL")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.ti IS NULL")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.cvd IS NULL")
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.created_at IS NULL")
    
    op.execute("COMMENT ON COLUMN metrics_volatility.id IS NULL")
    op.execute("COMMENT ON COLUMN metrics_volatility.symbol IS NULL")
    op.execute("COMMENT ON COLUMN metrics_volatility.timestamp IS NULL")
    op.execute("COMMENT ON COLUMN metrics_volatility.volatility_15m IS NULL")
    op.execute("COMMENT ON COLUMN metrics_volatility.volatility_30m IS NULL")
    op.execute("COMMENT ON COLUMN metrics_volatility.range_1m IS NULL")
    op.execute("COMMENT ON COLUMN metrics_volatility.range_1m_mean_15m IS NULL")
    op.execute("COMMENT ON COLUMN metrics_volatility.created_at IS NULL")
    
    op.execute("COMMENT ON COLUMN metrics_liquidity.id IS NULL")
    op.execute("COMMENT ON COLUMN metrics_liquidity.symbol IS NULL")
    op.execute("COMMENT ON COLUMN metrics_liquidity.timestamp IS NULL")
    op.execute("COMMENT ON COLUMN metrics_liquidity.acc_trade_price_24h IS NULL")
    op.execute("COMMENT ON COLUMN metrics_liquidity.liquidity_rank_7d IS NULL")
    op.execute("COMMENT ON COLUMN metrics_liquidity.created_at IS NULL")
    
    op.execute("COMMENT ON COLUMN monitored_symbols.id IS NULL")
    op.execute("COMMENT ON COLUMN monitored_symbols.symbol IS NULL")
    op.execute("COMMENT ON COLUMN monitored_symbols.is_active IS NULL")
    op.execute("COMMENT ON COLUMN monitored_symbols.created_at IS NULL")
    op.execute("COMMENT ON COLUMN monitored_symbols.updated_at IS NULL")


