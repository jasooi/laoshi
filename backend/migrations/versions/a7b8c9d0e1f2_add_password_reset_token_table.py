"""add_password_reset_token_table

Revision ID: a7b8c9d0e1f2
Revises: 67affe5c8824
Create Date: 2026-04-21 14:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = '67affe5c8824'
branch_labels = None
depends_on = None


def upgrade():
    # Only create if table doesn't already exist (may have been created via db.create_all())
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'password_reset_token' not in inspector.get_table_names():
        op.create_table(
            'password_reset_token',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
            sa.Column('token_hash', sa.String(128), unique=True, nullable=False, index=True),
            sa.Column('created_ds', sa.DateTime(), nullable=False),
            sa.Column('expires_ds', sa.DateTime(), nullable=False),
            sa.Column('used', sa.Boolean(), default=False, nullable=False),
        )


def downgrade():
    op.drop_table('password_reset_token')
