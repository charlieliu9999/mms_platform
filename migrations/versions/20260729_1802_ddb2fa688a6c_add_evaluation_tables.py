"""add_evaluation_tables

Revision ID: ddb2fa688a6c
Revises: 3d97fd5e6377
Create Date: 2026-07-29 18:02:24.452138
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


revision: str = 'ddb2fa688a6c'
down_revision: Union[str, None] = '3d97fd5e6377'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 eval_tasks 表
    op.create_table(
        'eval_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('test_file_path', sa.String(length=500), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('modality', sa.String(length=10), nullable=True),

        sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
        sa.Column('progress', sa.Integer(), nullable=True, server_default='0'),

        sa.Column('total_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('matched_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('wrong_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('no_match_count', sa.Integer(), nullable=True, server_default='0'),

        sa.Column('match_rate', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('accuracy', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('precision_score', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('recall_score', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('f1_score', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('avg_confidence', sa.DECIMAL(precision=5, scale=3), nullable=True),
        sa.Column('avg_response_time', sa.DECIMAL(precision=10, scale=2), nullable=True),

        sa.Column('dict_version', sa.String(length=50), nullable=True),
        sa.Column('dict_count', sa.Integer(), nullable=True),
        sa.Column('phrase_count', sa.Integer(), nullable=True),

        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),

        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('tags', ARRAY(sa.String(length=200)), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_eval_tasks_status', 'eval_tasks', ['status'])
    op.create_index('idx_eval_tasks_created_at', 'eval_tasks', ['created_at'])

    # 创建 eval_details 表
    op.create_table(
        'eval_details',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),

        sa.Column('check_item', sa.Text(), nullable=False),
        sa.Column('modality', sa.String(length=10), nullable=True),
        sa.Column('expected_code', sa.String(length=50), nullable=True),
        sa.Column('expected_name', sa.String(length=200), nullable=True),

        sa.Column('actual_code', sa.String(length=50), nullable=True),
        sa.Column('actual_name', sa.String(length=200), nullable=True),
        sa.Column('confidence', sa.DECIMAL(precision=5, scale=3), nullable=True),
        sa.Column('response_time', sa.DECIMAL(precision=10, scale=2), nullable=True),

        sa.Column('is_matched', sa.Boolean(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('match_type', sa.String(length=20), nullable=True),

        sa.Column('failure_reason', sa.String(length=50), nullable=True),
        sa.Column('failure_detail', sa.Text(), nullable=True),

        sa.Column('reviewed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('reviewer', sa.String(length=100), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('review_time', sa.TIMESTAMP(), nullable=True),

        sa.Column('suggested_action', sa.String(length=50), nullable=True),
        sa.Column('suggestion_data', JSONB(), nullable=True),

        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),

        sa.ForeignKeyConstraint(['task_id'], ['eval_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_eval_details_task_id', 'eval_details', ['task_id'])
    op.create_index('idx_eval_details_is_correct', 'eval_details', ['is_correct'])
    op.create_index('idx_eval_details_failure_reason', 'eval_details', ['failure_reason'])
    op.create_index('idx_eval_details_reviewed', 'eval_details', ['reviewed'])

    # 创建 optimization_suggestions 表
    op.create_table(
        'optimization_suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),

        sa.Column('suggestion_type', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='5'),

        sa.Column('word', sa.String(length=200), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=True),
        sa.Column('source_phrase', sa.String(length=200), nullable=True),
        sa.Column('target_phrase', sa.String(length=200), nullable=True),
        sa.Column('step', sa.String(length=50), nullable=True),

        sa.Column('affected_count', sa.Integer(), nullable=True),
        sa.Column('example_cases', ARRAY(sa.Text()), nullable=True),

        sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
        sa.Column('applied_at', sa.TIMESTAMP(), nullable=True),

        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),

        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),

        sa.ForeignKeyConstraint(['task_id'], ['eval_tasks.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_optimization_suggestions_task_id', 'optimization_suggestions', ['task_id'])
    op.create_index('idx_optimization_suggestions_status', 'optimization_suggestions', ['status'])
    op.create_index('idx_optimization_suggestions_priority', 'optimization_suggestions', ['priority'])

    # 创建 lexicon_versions 表
    op.create_table(
        'lexicon_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        sa.Column('medical_dict_count', sa.Integer(), nullable=True),
        sa.Column('phrase_map_count', sa.Integer(), nullable=True),
        sa.Column('ambiguity_rule_count', sa.Integer(), nullable=True),

        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('added_words', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('updated_words', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('deleted_words', sa.Integer(), nullable=True, server_default='0'),

        sa.Column('match_rate', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('accuracy', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('f1_score', sa.DECIMAL(precision=5, scale=2), nullable=True),

        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='false'),

        sa.Column('created_at', sa.TIMESTAMP(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('created_by', sa.String(length=100), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version')
    )

    print("✅ 评测系统表创建完成")


def downgrade() -> None:
    op.drop_table('lexicon_versions')
    op.drop_table('optimization_suggestions')
    op.drop_table('eval_details')
    op.drop_table('eval_tasks')

    print("✅ 评测系统表已删除")
