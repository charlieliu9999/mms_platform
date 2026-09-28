"""One catalog per modality; actual versions still come from standard rows."""

import re


SPECT_PELVIS_STANDARD_NAME = "SPECT常规静态骨显像"
SPECT_PELVIS_POLICY = "spect_pelvis_bone_only"


def spect_pelvis_bone_only(text: str) -> bool:
    """User-approved single procedure; never generalize to other hybrid scans."""
    normalized = re.sub(r"\s+", "", str(text)).translate(str.maketrans({
        "（": "(", "）": ")", "＋": "+", "／": "/",
    })).upper()
    return normalized == "SPECT/CT骨盆(骨显像+CT平扫)"


def is_spect_pelvis_policy_result(text: str, result: dict) -> bool:
    """Only approve the actual expected standard, not untrusted policy metadata."""
    if not spect_pelvis_bone_only(text):
        return False
    standards = [s for block in result.get("data", []) or []
                 if isinstance(block, dict)
                 for s in block.get("standard", []) or [] if isinstance(s, dict)]
    return (len(standards) == 1
            and re.sub(r"[\s*]+", "", str(standards[0].get("name", "")))
            == SPECT_PELVIS_STANDARD_NAME
            and bool(standards[0].get("code"))
            and bool(standards[0].get("version")))

MODALITY_CATALOG_VERSIONS = {
    "CT": "v3.8.2", "MR": "v3.8.2", "DR": "v3.8.2",
    "RF": "v3.8.2", "MG": "v3.8.2",
    "US": "v1.1", "PET/CT": "v1.1", "PET/MR": "v1.1",
    "DSA": "v2.0", "OCT": "v2.0", "SPECT": "v2.0",
}

# Some deployments retain the same modality catalog under its historical
# v3.8.2 label. Use it only when the entire active canonical catalog is absent;
# never fill individual canonical gaps from another version.
LEGACY_CATALOG_MODALITIES = frozenset({"US", "PET/CT", "PET/MR", "DSA", "OCT", "SPECT"})


def _catalog_clause(modality: str, canonical_version: str) -> str:
    canonical = f"UPPER(TRIM(version)) = '{canonical_version.upper()}'"
    if modality in LEGACY_CATALOG_MODALITIES:
        canonical = (
            f"({canonical} OR (UPPER(TRIM(version)) = 'V3.8.2' AND NOT EXISTS ("
            "SELECT 1 FROM standard_check_items AS primary_catalog "
            "WHERE primary_catalog.is_active = true "
            f"AND primary_catalog.modality = '{modality}' "
            f"AND UPPER(TRIM(primary_catalog.version)) = '{canonical_version.upper()}'"
            ")))"
        )
    return f"(modality = '{modality}' AND {canonical})"


# Static internal policy, never interpolated from request input. Both the
# exact-name loader and keyword loader use this identical selection predicate.
CATALOG_POLICY_SQL = "(" + " OR ".join(
    _catalog_clause(modality, version)
    for modality, version in MODALITY_CATALOG_VERSIONS.items()
) + ")"
