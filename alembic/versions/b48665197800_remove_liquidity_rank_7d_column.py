"""Remove liquidity_rank_7d column

Revision ID: b48665197800
Revises: 3ab9742a6143
Create Date: 2026-01-03 21:55:58.312616

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b48665197800'
down_revision = '3ab9742a6143'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # liquidity_rank_7d 컬럼 제거
    op.drop_column('metrics_liquidity', 'liquidity_rank_7d')


def downgrade() -> None:
    # 컬럼 복구
    op.add_column('metrics_liquidity', sa.Column('liquidity_rank_7d', sa.Numeric(10, 2), nullable=True))


