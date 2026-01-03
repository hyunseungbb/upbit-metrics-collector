"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2025-01-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum 타입 생성
    op.execute("CREATE TYPE orderside AS ENUM ('BUY', 'SELL')")
    
    # 스프레드 평가지표 테이블
    op.create_table(
        'metrics_spread',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('spread_bps', sa.Numeric(10, 4), nullable=False),
        sa.Column('mid_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('spread_bps_ema_10s', sa.Numeric(10, 4), nullable=True),
        sa.Column('spread_bps_mean_60s', sa.Numeric(10, 4), nullable=True),
        sa.Column('spread_bps_p95_5m', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_metrics_spread_symbol', 'metrics_spread', ['symbol'])
    op.create_index('idx_metrics_spread_timestamp', 'metrics_spread', ['timestamp'])
    op.create_index('idx_metrics_spread_symbol_timestamp', 'metrics_spread', ['symbol', 'timestamp'])
    
    # 오더북 불균형 평가지표 테이블
    op.create_table(
        'metrics_orderbook_imbalance',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('imbalance', sa.Numeric(5, 4), nullable=False),
        sa.Column('bid_volume', sa.Numeric(20, 8), nullable=False),
        sa.Column('ask_volume', sa.Numeric(20, 8), nullable=False),
        sa.Column('imbalance_ema_5s', sa.Numeric(5, 4), nullable=True),
        sa.Column('imbalance_ema_30s', sa.Numeric(5, 4), nullable=True),
        sa.Column('imbalance_mean_5m', sa.Numeric(5, 4), nullable=True),
        sa.Column('imbalance_zscore_24h', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_metrics_orderbook_imbalance_symbol', 'metrics_orderbook_imbalance', ['symbol'])
    op.create_index('idx_metrics_orderbook_imbalance_timestamp', 'metrics_orderbook_imbalance', ['timestamp'])
    op.create_index('idx_metrics_orderbook_imbalance_symbol_timestamp', 'metrics_orderbook_imbalance', ['symbol', 'timestamp'])
    
    # 슬리피지 평가지표 테이블
    op.create_table(
        'metrics_slippage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('order_size_krw', sa.Numeric(20, 2), nullable=False),
        sa.Column('side', postgresql.ENUM('BUY', 'SELL', name='orderside', create_type=False), nullable=False),
        sa.Column('slippage_bps', sa.Numeric(10, 4), nullable=False),
        sa.Column('slippage_bps_ema_30s', sa.Numeric(10, 4), nullable=True),
        sa.Column('slippage_bps_mean_5m', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_metrics_slippage_symbol', 'metrics_slippage', ['symbol'])
    op.create_index('idx_metrics_slippage_timestamp', 'metrics_slippage', ['timestamp'])
    op.create_index('idx_metrics_slippage_symbol_timestamp', 'metrics_slippage', ['symbol', 'timestamp'])
    
    # 체결 방향 비율 평가지표 테이블
    op.create_table(
        'metrics_trade_imbalance',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('window_minutes', sa.Integer(), nullable=False),
        sa.Column('buy_volume', sa.Numeric(20, 8), nullable=False),
        sa.Column('sell_volume', sa.Numeric(20, 8), nullable=False),
        sa.Column('ti', sa.Numeric(5, 4), nullable=False),
        sa.Column('cvd', sa.Numeric(20, 8), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_metrics_trade_imbalance_symbol', 'metrics_trade_imbalance', ['symbol'])
    op.create_index('idx_metrics_trade_imbalance_timestamp', 'metrics_trade_imbalance', ['timestamp'])
    op.create_index('idx_metrics_trade_imbalance_symbol_timestamp', 'metrics_trade_imbalance', ['symbol', 'timestamp'])
    op.create_index('idx_metrics_trade_imbalance_symbol_window', 'metrics_trade_imbalance', ['symbol', 'window_minutes'])
    
    # 변동성 평가지표 테이블
    op.create_table(
        'metrics_volatility',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('volatility_15m', sa.Numeric(10, 6), nullable=True),
        sa.Column('volatility_30m', sa.Numeric(10, 6), nullable=True),
        sa.Column('range_1m', sa.Numeric(10, 6), nullable=True),
        sa.Column('range_1m_mean_15m', sa.Numeric(10, 6), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_metrics_volatility_symbol', 'metrics_volatility', ['symbol'])
    op.create_index('idx_metrics_volatility_timestamp', 'metrics_volatility', ['timestamp'])
    op.create_index('idx_metrics_volatility_symbol_timestamp', 'metrics_volatility', ['symbol', 'timestamp'])
    
    # 유동성 평가지표 테이블
    op.create_table(
        'metrics_liquidity',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('acc_trade_price_24h', sa.Numeric(20, 2), nullable=False),
        sa.Column('liquidity_rank_7d', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_metrics_liquidity_symbol', 'metrics_liquidity', ['symbol'])
    op.create_index('idx_metrics_liquidity_timestamp', 'metrics_liquidity', ['timestamp'])
    op.create_index('idx_metrics_liquidity_symbol_timestamp', 'metrics_liquidity', ['symbol', 'timestamp'])
    
    # 모니터링 종목 테이블
    op.create_table(
        'monitored_symbols',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('symbol', sa.String(20), nullable=False, unique=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    # updated_at 자동 업데이트 트리거 생성
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    op.execute("""
        CREATE TRIGGER update_monitored_symbols_updated_at
        BEFORE UPDATE ON monitored_symbols
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)
    op.create_index('idx_monitored_symbols_symbol', 'monitored_symbols', ['symbol'])
    op.create_index('idx_monitored_symbols_is_active', 'monitored_symbols', ['is_active'])


def downgrade() -> None:
    op.execute('DROP TRIGGER IF EXISTS update_monitored_symbols_updated_at ON monitored_symbols')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    op.drop_table('monitored_symbols')
    op.drop_table('metrics_liquidity')
    op.drop_table('metrics_volatility')
    op.drop_table('metrics_trade_imbalance')
    op.drop_table('metrics_slippage')
    op.drop_table('metrics_orderbook_imbalance')
    op.drop_table('metrics_spread')
    op.execute('DROP TYPE IF EXISTS orderside')

