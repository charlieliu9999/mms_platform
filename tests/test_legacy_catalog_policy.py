"""Execute the shared selection SQL over realistic mixed-version catalogs."""
import sqlite3

import pytest
from sqlalchemy import text

from match_service.engine.catalog_policy import CATALOG_POLICY_SQL, MODALITY_CATALOG_VERSIONS


def select_catalog(rows):
    # Real SQL execution in a process-local fixture; no shared DB writes.
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE standard_check_items (item_code TEXT, modality TEXT, version TEXT, is_active BOOLEAN)")
        connection.executemany("INSERT INTO standard_check_items VALUES (?, ?, ?, ?)", rows)
        return connection.execute(
            "SELECT item_code, modality, version FROM standard_check_items "
            "WHERE is_active = true AND " + CATALOG_POLICY_SQL + " ORDER BY item_code"
        ).fetchall()


@pytest.mark.parametrize("modality", ["US", "PET/CT", "PET/MR", "SPECT", "OCT", "DSA"])
def test_canonical_catalog_wins_over_legacy_and_unknown_versions(modality):
    canonical = MODALITY_CATALOG_VERSIONS[modality]
    actual_label = f" {canonical.upper()} "
    rows = [("canonical", modality, actual_label, True),
            ("legacy", modality, "V3.8.2", True),
            ("old-us", modality, "v1.0", True),
            ("unknown", modality, "v99", True)]
    assert select_catalog(rows) == [("canonical", modality, actual_label)]


@pytest.mark.parametrize("modality", ["US", "PET/CT", "PET/MR", "SPECT", "OCT", "DSA"])
def test_missing_active_canonical_catalog_uses_only_legacy_actual_label(modality):
    canonical = MODALITY_CATALOG_VERSIONS[modality]
    rows = [("inactive-canonical", modality, canonical, False),
            ("legacy", modality, " V3.8.2 ", True),
            ("old-us", modality, "v1.0", True),
            ("unknown", modality, "v99", True)]
    assert select_catalog(rows) == [("legacy", modality, " V3.8.2 ")]


def test_fallback_is_per_modality_and_never_fills_a_canonical_gap():
    rows = [("us-canonical-one", "US", "v1.1", True),
            ("us-legacy-other", "US", "v3.8.2", True),
            ("pet-legacy", "PET/CT", "v3.8.2", True),
            ("dsa-canonical", "DSA", "v2.0", True),
            ("dsa-duplicate", "DSA", "v3.8.2", True)]
    assert select_catalog(rows) == [
        ("dsa-canonical", "DSA", "v2.0"),
        ("pet-legacy", "PET/CT", "v3.8.2"),
        ("us-canonical-one", "US", "v1.1"),
    ]


def test_unknown_only_or_inactive_legacy_catalog_is_not_selected():
    assert select_catalog([("unknown", "US", "v1.0", True),
                           ("inactive", "SPECT", "v3.8.2", False)]) == []


def test_nlp_catalogs_do_not_gain_historical_or_unknown_fallbacks():
    rows = [("ct-selected", "CT", "v3.8.2", True),
            ("ct-new", "CT", "v4.0.0", True),
            ("mr-wrong", "MR", "v2.0", True),
            ("unsupported", "UNKNOWN", "v3.8.2", True)]
    assert select_catalog(rows) == [("ct-selected", "CT", "v3.8.2")]


@pytest.mark.asyncio
async def test_postgres_readonly_cte_selects_actual_labels_without_table_writes():
    from match_service.db import get_engine

    # VALUES shadows the table for this SELECT only. It exercises the real
    # PostgreSQL predicate over production-like data without creating anything.
    query = """
        WITH standard_check_items(item_code, modality, version, is_active) AS (
            VALUES ('us-legacy', 'US', ' V3.8.2 ', true),
                   ('us-old', 'US', 'v1.0', true),
                   ('us-inactive', 'US', 'v1.1', false),
                   ('pet-legacy', 'PET/CT', 'V3.8.2', true),
                   ('spect-legacy', 'SPECT', 'V3.8.2', true),
                   ('oct-legacy', 'OCT', 'V3.8.2', true),
                   ('dsa-canonical', 'DSA', 'v2.0', true),
                   ('dsa-duplicate', 'DSA', 'V3.8.2', true)
        ) SELECT item_code, modality, version FROM standard_check_items
        WHERE is_active = true AND """ + CATALOG_POLICY_SQL + " ORDER BY item_code"
    async with get_engine().connect() as connection:
        rows = (await connection.execute(text(query))).fetchall()
    assert [tuple(row) for row in rows] == [
        ("dsa-canonical", "DSA", "v2.0"),
        ("oct-legacy", "OCT", "V3.8.2"),
        ("pet-legacy", "PET/CT", "V3.8.2"),
        ("spect-legacy", "SPECT", "V3.8.2"),
        ("us-legacy", "US", " V3.8.2 "),
    ]
