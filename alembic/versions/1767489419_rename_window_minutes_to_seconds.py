"""Rename window_minutes to window_seconds

Revision ID: 1767489419
Revises: b48665197800
Create Date: 2026-01-04 01:03:39.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1767489419'
down_revision = 'b48665197800'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 컬럼명 변경: window_minutes → window_seconds
    # 기존 데이터는 그대로 유지 (30 → 30, 60 → 60)
    op.alter_column(
        'metrics_trade_imbalance',
        'window_minutes',
        new_column_name='window_seconds',
        existing_type=sa.Integer(),
        existing_nullable=False
    )
    
    # 인덱스 이름도 변경
    op.drop_index('idx_metrics_trade_imbalance_symbol_window', table_name='metrics_trade_imbalance')
    op.create_index(
        'idx_metrics_trade_imbalance_symbol_window',
        'metrics_trade_imbalance',
        ['symbol', 'window_seconds']
    )
    
    # 컬럼 COMMENT 업데이트
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.window_seconds IS '롤링 윈도우 크기 (초 단위: 30초=30, 60초=60)'")


def downgrade() -> None:
    # 컬럼명 복구: window_seconds → window_minutes
    op.alter_column(
        'metrics_trade_imbalance',
        'window_seconds',
        new_column_name='window_minutes',
        existing_type=sa.Integer(),
        existing_nullable=False
    )
    
    # 인덱스 이름 복구
    op.drop_index('idx_metrics_trade_imbalance_symbol_window', table_name='metrics_trade_imbalance')
    op.create_index(
        'idx_metrics_trade_imbalance_symbol_window',
        'metrics_trade_imbalance',
        ['symbol', 'window_minutes']
    )
    
    # 컬럼 COMMENT 복구
    op.execute("COMMENT ON COLUMN metrics_trade_imbalance.window_minutes IS '롤링 윈도우 크기 (분, 실제로는 30초/60초)'")

