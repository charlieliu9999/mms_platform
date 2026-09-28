"""Bootstrap the exact MMS-owned schema, including Admin and provenance.

Historical rule migrations cannot bootstrap an empty database. Keep this schema
lineage separate from alembic_version. No source connection is needed at runtime.
"""
from pathlib import Path
from alembic import op

revision = "20260926_0100"
down_revision = None
branch_labels = None
depends_on = None

TABLES = (
    "nlp_medical_dict", "nlp_phrase_map", "nlp_ambiguity",
    "standard_check_items", "match_cache", "match_feedback",
    "lexicon_suggestion", "procedure_dictionary", "procedure_match_results",
    "unmatched_registry", "keyword_match_rules", "mms_eval_tasks",
    "mms_eval_details", "mms_lexicon_versions", "mms_optimization_suggestions",
    "technical_detail_candidates", "technical_detail_candidate_revisions",
    "technical_detail_provenance", "technical_detail_publications", "alembic_version",
)


def upgrade():
    schema = (Path(__file__).parent.parent / "schema.sql").read_text()
    # asyncpg's simple-query protocol executes the complete DDL script without
    # unsafe splitting of semicolons in quoted SQL comments or defaults.
    op.get_bind().connection.run_async(lambda connection: connection.execute(schema))
    op.execute("SET search_path TO public")


def downgrade():
    # Drop together to resolve internal FKs. Unexpected external dependencies
    # block rollback: deliberately omit CASCADE.
    names = ", ".join('public."' + name + '"' for name in TABLES)
    op.execute("DROP TABLE " + names)

