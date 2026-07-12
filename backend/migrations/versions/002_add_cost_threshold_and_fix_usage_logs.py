"""Phase 9: Add cost_threshold to projects and restructure usage_logs.

Revision ID: 002
Revises: 001
Create Date: 2026-07-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cost_threshold to projects
    op.add_column('projects', sa.Column('cost_threshold', sa.Float(), nullable=False, server_default='10.0'))

    # Drop old usage_logs table
    op.drop_table('usage_logs')

    # Create new usage_logs table with updated schema
    op.create_table(
        'usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('gpt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tts_characters', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('render_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usage_logs_id'), 'usage_logs', ['id'], unique=False)
    op.create_index(op.f('ix_usage_logs_project_id'), 'usage_logs', ['project_id'], unique=False)


def downgrade() -> None:
    # Drop new usage_logs table
    op.drop_index(op.f('ix_usage_logs_project_id'), table_name='usage_logs')
    op.drop_index(op.f('ix_usage_logs_id'), table_name='usage_logs')
    op.drop_table('usage_logs')

    # Recreate old usage_logs table
    op.create_table(
        'usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('usage_type', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usage_logs_usage_type'), 'usage_logs', ['usage_type'], unique=False)
    op.create_index(op.f('ix_usage_logs_id'), 'usage_logs', ['id'], unique=False)

    # Drop cost_threshold from projects
    op.drop_column('projects', 'cost_threshold')
