"""add_mms_evaluation_tables

Revision ID: 33a6ffc77484
Revises: ddb2fa688a6c
Create Date: 2026-07-29 18:04:01.863205

创建 MMS 评测系统表，统一使用 mms_ 前缀，避免与库内既有的
eval_tasks / eval_task_details（其他系统）命名冲突。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


revision: str = '33a6ffc77484'
down_revision: Union[str, None] = 'ddb2fa688a6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- mms_eval_tasks：评测任务 ----
    op.create_table(
        'mms_eval_tasks',
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

        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_mms_eval_tasks_status', 'mms_eval_tasks', ['status'])
    op.create_index('idx_mms_eval_tasks_created_at', 'mms_eval_tasks', ['created_at'])

    # ---- mms_eval_details：逐条评测结果 ----
    op.create_table(
        'mms_eval_details',
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

        sa.ForeignKeyConstraint(['task_id'], ['mms_eval_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_mms_eval_details_task_id', 'mms_eval_details', ['task_id'])
    op.create_index('idx_mms_eval_details_is_correct', 'mms_eval_details', ['is_correct'])
    op.create_index('idx_mms_eval_details_failure_reason', 'mms_eval_details', ['failure_reason'])
    op.create_index('idx_mms_eval_details_reviewed', 'mms_eval_details', ['reviewed'])

    # ---- mms_optimization_suggestions：优化建议 ----
    op.create_table(
        'mms_optimization_suggestions',
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

        sa.ForeignKeyConstraint(['task_id'], ['mms_eval_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_mms_opt_suggestions_task_id', 'mms_optimization_suggestions', ['task_id'])
    op.create_index('idx_mms_opt_suggestions_status', 'mms_optimization_suggestions', ['status'])
    op.create_index('idx_mms_opt_suggestions_priority', 'mms_optimization_suggestions', ['priority'])

    # ---- mms_lexicon_versions：词表版本 ----
    op.create_table(
        'mms_lexicon_versions',
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
        sa.UniqueConstraint('version'),
    )


def downgrade() -> None:
    op.drop_table('mms_lexicon_versions')
    op.drop_table('mms_optimization_suggestions')
    op.drop_table('mms_eval_details')
    op.drop_table('mms_eval_tasks')
