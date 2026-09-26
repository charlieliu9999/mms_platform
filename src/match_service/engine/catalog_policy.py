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

# Static internal policy, never interpolated from request input.
CATALOG_POLICY_SQL = "(" + " OR ".join(
    f"(modality = '{modality}' AND UPPER(TRIM(version)) = '{version.upper()}')"
    for modality, version in MODALITY_CATALOG_VERSIONS.items()
) + ")"
