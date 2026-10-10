"""add image_url to products

Revision ID: 6de9a6ad6a22
Revises: bb4b470d71c2
Create Date: 2026-10-10 13:39:39.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6de9a6ad6a22'
down_revision = 'bb4b470d71c2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_url', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('image_url')
