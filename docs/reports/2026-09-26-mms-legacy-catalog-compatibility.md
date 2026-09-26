# MMS legacy catalog compatibility

Branch: `codex/mms-legacy-catalog-compat`.
Base: `52aca9c5c9a70047992b0e49964c9dcc8dec3b76`.
Reviewed by the integration owner; VPS acceptance is recorded separately.

## Problem and scope

The deployment coordinator found that some production modality catalogs still
carry their actual historical `V3.8.2` database label. A canonical-only SQL
predicate consequently omitted active US/PET/SPECT/OCT rows. This task changes
catalog selection only, without relabeling or editing any standard data.

`catalog_policy.py` provides the same predicate to the exact-name loader and
keyword loader. No loader call-site change is needed. CT/MR/DR/RF/MG remain
restricted to v3.8.2. US/PET-CT/PET-MR prefer v1.1, and SPECT/OCT/DSA prefer
v2.0. For the six keyword modalities, active v3.8.2 rows are selected only if
that entire modality has no active canonical row. The `NOT EXISTS` check is
scoped to the same modality and considers active rows only.

There is still exactly one catalog per modality. Canonical catalogs cannot be
supplemented from legacy rows to fill individual gaps. DSA with active v2.0
rows does not load duplicate v3.8.2 rows. US v1.0, unknown versions, inactive
rows and unsupported modalities remain excluded. Selected row labels are
returned unchanged; no canonical version is inferred or fabricated.

## Validation

15 new meaningful tests execute the actual shared SQL in process-local SQLite
fixtures, covering all six modalities, mixed-case/whitespace version labels,
inactive canonical rows, unknown versions, per-modality independence, DSA
duplication and no cross-version gap filling. One additional PostgreSQL test
uses a read-only VALUES CTE to shadow the table for that SELECT, proving the
legacy US/PET/SPECT/OCT and canonical DSA selection on the actual database
dialect without creating or writing any database object. Existing full-suite
loader integration tests also execute the predicate against read-only data.

- Focused policy/metadata suite: 53 passed.
- Full backend suite: 263 passed, 2 skipped, 4 warnings.
- Defect ruff and `git diff --check`: passed.
- Same-data 4555 comparison: 3919 before and after; all complete result records
  are identical, including codes, names, actual versions, tiers and reasons.
- Before/after rule fingerprint: `v15030-a0c140d8a1ce`.
- Modified source SHA-256:
  `0fd9e367a7122fb6ef7053b038d34c9f7cfbcfba506b69ad1d9f3c786b167350`.

Tests used the existing MMS virtual environment with
`PGOPTIONS='-c default_transaction_read_only=on'` and a wrapper enforcing
read-only local asyncpg connections. Evaluation used read-only local rules
from `acrac_db` and the frozen inputs from `mms_mms2_verify`. No shared runtime,
database content or VPS was operated by this task.

Artifacts in `outputs/t424/` are `baseline-legacy-catalog-4555.json`,
`after-legacy-catalog-4555.json`, `legacy-catalog-focused-tests.log` and
`legacy-catalog-full-tests.log`.

## Limits and release checks

The local canonical data does not prove production legacy content is clinically
equivalent. The deployment owner must verify actual legacy US availability,
returned database versions, DSA nonduplication and baseline CT/MR behavior on
the production candidate before activation. Clinical-policy changes are out of
scope. A partial canonical catalog intentionally prevents legacy gap filling.

The approved SPECT/CT pelvis procedure remains SPECT-only. If its exact active
SPECT standard is absent, matching fails safely for review; this change creates
no standard and introduces no CT fallback. The deployment coordinator reported
that the required SPECT code is absent in production, which remains a known
standard-library gap rather than a reason to fabricate a match.
