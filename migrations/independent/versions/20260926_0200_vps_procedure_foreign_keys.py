"""Preserve the three procedure foreign keys audited on the VPS source.

This revision belongs to the VPS release lineage. The local source did not
have these constraints; do not rewrite the already applied bootstrap revision.
"""
from alembic import op

revision = "20260926_0200"
down_revision = "20260926_0100"
branch_labels = None
depends_on = None

FOREIGN_KEYS = (
    ("standard_check_items", "linked_procedure_id", None),
    ("procedure_match_results", "procedure_id", "CASCADE"),
    ("unmatched_registry", "procedure_id", None),
)


def upgrade():
    for table, column, ondelete in FOREIGN_KEYS:
        op.create_foreign_key(
            f"{table}_{column}_fkey", table, "procedure_dictionary",
            [column], ["id"], ondelete=ondelete,
        )


def downgrade():
    for table, column, _ in reversed(FOREIGN_KEYS):
        op.drop_constraint(f"{table}_{column}_fkey", table, type_="foreignkey")
