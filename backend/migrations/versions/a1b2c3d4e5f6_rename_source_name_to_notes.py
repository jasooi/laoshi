"""Rename source_name to notes on word table

Revision ID: a1b2c3d4e5f6
Revises: 55a8f913d279
Create Date: 2026-03-14 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '55a8f913d279'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('word', schema=None) as batch_op:
        batch_op.alter_column('source_name', new_column_name='notes')


def downgrade():
    with op.batch_alter_table('word', schema=None) as batch_op:
        batch_op.alter_column('notes', new_column_name='source_name')
