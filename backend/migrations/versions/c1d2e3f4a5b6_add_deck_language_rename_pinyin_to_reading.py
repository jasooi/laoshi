"""add deck language and rename word pinyin to reading

Revision ID: c1d2e3f4a5b6
Revises: b8c9d0e1f2a3
Create Date: 2026-05-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    # Add language column to deck table with server default 'ZH'
    op.add_column('deck', sa.Column('language', sa.String(2), nullable=False, server_default='ZH'))

    # Rename word.pinyin to word.reading
    with op.batch_alter_table('word') as batch_op:
        batch_op.alter_column('pinyin', new_column_name='reading')


def downgrade():
    # Rename word.reading back to word.pinyin
    with op.batch_alter_table('word') as batch_op:
        batch_op.alter_column('reading', new_column_name='pinyin')

    # Drop language column from deck table
    op.drop_column('deck', 'language')
