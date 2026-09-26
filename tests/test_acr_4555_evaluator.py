"""Contract tests for the canonical ACR 4555 evaluator."""

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/evaluate_acr_4555.py"
SPEC = importlib.util.spec_from_file_location("evaluate_acr_4555", SCRIPT)
evaluator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluator)


def _write_manifest(tmp_path, rows, expected_count):
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["semantic_id", "name_zh", "modality"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    metadata = tmp_path / "manifest.meta.json"
    metadata.write_text(
        json.dumps(
            {
                "dataset_id": evaluator.EXPECTED_DATASET_ID,
                "dataset_version": "test-v1",
                "expected_count": expected_count,
                "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return manifest, metadata


def test_repository_manifest_is_exact_and_self_verifying():
    rows, metadata = evaluator.load_manifest()

    assert len(rows) == 4555
    assert len({row["semantic_id"] for row in rows}) == 4555
    assert rows[0]["semantic_id"] == "PR0001"
    assert rows[-1]["semantic_id"] == "PR4884"
    assert metadata["manifest_sha256"] == evaluator.sha256_file(
        evaluator.DEFAULT_MANIFEST
    )


def test_manifest_hash_mismatch_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluator, "EXPECTED_COUNT", 1)
    manifest, metadata = _write_manifest(
        tmp_path,
        [{"semantic_id": "PR0001", "name_zh": "头颅CT", "modality": "CT"}],
        1,
    )
    manifest.write_text(manifest.read_text() + "\n", encoding="utf-8")

    with pytest.raises(evaluator.DatasetContractError, match="SHA-256"):
        evaluator.load_manifest(manifest, metadata)


def test_live_cohort_content_drift_fails_closed(monkeypatch):
    monkeypatch.setattr(evaluator, "EXPECTED_COUNT", 1)
    manifest = [{"semantic_id": "PR0001", "name_zh": "头颅CT", "modality": "CT"}]

    with pytest.raises(evaluator.DatasetContractError, match="changed=.*PR0001"):
        evaluator.validate_live_rows([(1, "PR0001", "胸部CT", "CT")], manifest)


def test_summary_contains_per_modality_totals():
    summary = evaluator.build_summary(
        [
            {"modality": "CT", "matched": True, "reason": None},
            {"modality": "CT", "matched": False, "reason": "lexicon_gap"},
            {"modality": "MR", "matched": True, "reason": None},
        ]
    )

    assert summary["total"] == 3
    assert summary["matched"] == 2
    assert summary["by_modality"]["CT"] == {
        "total": 2,
        "matched": 1,
        "unmatched": 1,
        "match_rate": 50.0,
    }


def test_snapshot_compare_rejects_dataset_mismatch():
    current = {
        "snapshot_schema_version": 2,
        "dataset": {"dataset_id": "acr-4555-pr-v1", "manifest_sha256": "new"},
        "results": [],
    }
    baseline = {
        "snapshot_schema_version": 2,
        "dataset": {"dataset_id": "acr-4555-pr-v1", "manifest_sha256": "old"},
        "results": [],
    }

    with pytest.raises(evaluator.DatasetContractError, match="datasets differ"):
        evaluator.compare_snapshots(current, baseline)


@pytest.mark.asyncio
async def test_engine_exception_is_recorded_without_secondary_logger_error(monkeypatch):
    async def load_rows(factory, manifest):
        return [{"database_id": 1, "semantic_id": "PR0001", "name_zh": "CT头部", "modality": "CT"}]

    class BrokenEngine:
        def match(self, name, modality):
            raise RuntimeError("simulated engine failure")

    monkeypatch.setattr(evaluator, "load_canonical_rows", load_rows)
    rows = await evaluator.run_eval(BrokenEngine(), object(), [])
    assert len(rows) == 1
    assert rows[0]["matched"] is False
    assert rows[0]["tier"] == "error"
    assert rows[0]["reason"] == "engine_error"


def test_snapshot_standards_keep_actual_version():
    result = {"data": [{"standard": [{"code": "c", "name": "US标准", "version": "v1.1"}]}]}
    assert evaluator.extract_standards(result) == [{"code": "c", "name": "US标准", "version": "v1.1"}]


def test_semantic_conflict_has_its_own_reason():
    assert evaluator.classify_unmatched({"tier": "none", "has_entity": True, "reason": "standard_semantic_conflict"})[0] == "standard_semantic_conflict"
    reason, detail = evaluator.classify_unmatched({"tier": "ambiguous", "reason": "multiple_technical_candidates", "unresolved_components": ["颈部静脉"]})
    assert reason == "parser_ambiguity"
    assert "颈部静脉" in detail


@pytest.mark.asyncio
@pytest.mark.parametrize("semantic_id", ["PR1181", "PR3575"])
async def test_engine_internal_routing_uses_dispatcher_review_policy(monkeypatch, semantic_id):
    """Breast X-ray + US candidates require review, including internal routing."""
    async def load_rows(factory, manifest):
        return [{"database_id": 1, "semantic_id": semantic_id,
                 "name_zh": "乳腺X线摄影及超声检查", "modality": "DR"}]

    class RoutedEngine:
        def match(self, name, modality):
            return {"tier": "degraded", "num_standard": 1,
                    "modality_routed": True, "effective_modality": "MG",
                    "data": [{"standard": [{"code": "mg", "name": "乳腺X线摄影"}]}]}

    monkeypatch.setattr(evaluator, "load_canonical_rows", load_rows)
    monkeypatch.setattr(evaluator, "resolve_effective_modality", lambda name, source: source)
    rows = await evaluator.run_eval(RoutedEngine(), object(), [])

    assert rows[0]["matched"] is False
    assert rows[0]["tier"] == "ambiguous"
    assert rows[0]["reason"] == "modality_route_review"
