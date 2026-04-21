"""add_cascade_deletes_to_foreign_keys

Revision ID: b8c9d0e1f2a3
Revises: 67affe5c8824
Create Date: 2026-04-21 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8c9d0e1f2a3'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def _find_fk_name(inspector, table_name, constrained_columns):
    """Find the actual FK constraint name by matching constrained columns."""
    for fk in inspector.get_foreign_keys(table_name):
        if fk['constrained_columns'] == constrained_columns:
            return fk['name']
    return None


def _replace_fk(inspector, table_name, columns, ref_table, ref_columns, ondelete):
    """Drop existing FK and recreate with new ondelete behavior."""
    fk_name = _find_fk_name(inspector, table_name, columns)
    if fk_name is None:
        return
    new_name = f"{table_name}_{'_'.join(columns)}_fkey"
    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.drop_constraint(fk_name, type_='foreignkey')
        batch_op.create_foreign_key(new_name, ref_table, columns, ref_columns, ondelete=ondelete)


def _revert_fk(inspector, table_name, columns, ref_table, ref_columns):
    """Revert FK back to default (no ondelete action)."""
    fk_name = _find_fk_name(inspector, table_name, columns)
    if fk_name is None:
        return
    new_name = f"{table_name}_{'_'.join(columns)}_fkey"
    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.drop_constraint(fk_name, type_='foreignkey')
        batch_op.create_foreign_key(new_name, ref_table, columns, ref_columns)


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Deck.user_id → CASCADE
    if 'deck' in tables:
        _replace_fk(inspector, 'deck', ['user_id'], 'user', ['id'], 'CASCADE')

    # Word.user_id → CASCADE, Word.deck_id → CASCADE
    if 'word' in tables:
        _replace_fk(inspector, 'word', ['user_id'], 'user', ['id'], 'CASCADE')
        _replace_fk(inspector, 'word', ['deck_id'], 'deck', ['id'], 'CASCADE')

    # UserSession.user_id → CASCADE, UserSession.deck_id → SET NULL
    if 'user_session' in tables:
        _replace_fk(inspector, 'user_session', ['user_id'], 'user', ['id'], 'CASCADE')
        _replace_fk(inspector, 'user_session', ['deck_id'], 'deck', ['id'], 'SET NULL')

    # SessionWord.word_id → CASCADE, SessionWord.session_id → CASCADE
    if 'session_word' in tables:
        _replace_fk(inspector, 'session_word', ['word_id'], 'word', ['id'], 'CASCADE')
        _replace_fk(inspector, 'session_word', ['session_id'], 'user_session', ['id'], 'CASCADE')

    # SessionWordAttempt composite FK → CASCADE
    if 'session_word_attempt' in tables:
        _replace_fk(
            inspector, 'session_word_attempt',
            ['word_id', 'session_id'], 'session_word', ['word_id', 'session_id'],
            'CASCADE',
        )

    # UserProfile.user_id → CASCADE
    if 'user_profile' in tables:
        _replace_fk(inspector, 'user_profile', ['user_id'], 'user', ['id'], 'CASCADE')

    # PasswordResetToken.user_id → CASCADE (table may not exist yet)
    if 'password_reset_token' in tables:
        _replace_fk(inspector, 'password_reset_token', ['user_id'], 'user', ['id'], 'CASCADE')


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'password_reset_token' in tables:
        _revert_fk(inspector, 'password_reset_token', ['user_id'], 'user', ['id'])

    if 'user_profile' in tables:
        _revert_fk(inspector, 'user_profile', ['user_id'], 'user', ['id'])

    if 'session_word_attempt' in tables:
        _revert_fk(
            inspector, 'session_word_attempt',
            ['word_id', 'session_id'], 'session_word', ['word_id', 'session_id'],
        )

    if 'session_word' in tables:
        _revert_fk(inspector, 'session_word', ['session_id'], 'user_session', ['id'])
        _revert_fk(inspector, 'session_word', ['word_id'], 'word', ['id'])

    if 'user_session' in tables:
        _revert_fk(inspector, 'user_session', ['deck_id'], 'deck', ['id'])
        _revert_fk(inspector, 'user_session', ['user_id'], 'user', ['id'])

    if 'word' in tables:
        _revert_fk(inspector, 'word', ['deck_id'], 'deck', ['id'])
        _revert_fk(inspector, 'word', ['user_id'], 'user', ['id'])

    if 'deck' in tables:
        _revert_fk(inspector, 'deck', ['user_id'], 'user', ['id'])
