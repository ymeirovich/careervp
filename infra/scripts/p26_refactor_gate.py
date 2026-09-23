"""P-26 Job-1 refactor gate — enforce the STOP conditions before any execute.

Validates the flag-ON cloud assembly (and, if provided, the ``cdk refactor
--dry-run`` output) against the P-26 Job-1 invariants. Exits non-zero on ANY
violation so CI (and a human operator) can hard-stop before executing the
human-gated ``cdk refactor``. This script performs NO AWS calls and mutates
nothing; it only reads synthesized templates + a captured dry-run log.

Usage:
    uv run python scripts/p26_refactor_gate.py \
        --synth-on cdk.out.on \
        [--refactor-out refactor_dryrun.out] \
        [--parent-max 400] [--template-max 500]

Gates (each maps to a STOP condition in the step brief):
  1. Parent ``CareerVpCrudDev`` template resource count < ``--parent-max``.
  2. No stack template (parent or nested) >= ``--template-max``.
  3. RestApi + Cognito user-pool/client logical ids are PRESENT in the parent,
     byte-identical, and ABSENT from the CrudFeatures nested template (IMMUTABLE).
  4. The 76 real re-homed logical ids (``careervp.rehome_map`` minus the dormant
     P-24 authorizer) are PRESENT in CrudFeatures and ABSENT from the parent
     (byte-stable move).
  5. If a refactor dry-run log is supplied: it did not error, the RestApi/Cognito
     logical ids never appear in it, and it contains no DELETE/CREATE/REPLACE of a
     named resource (moves/renames only).
  6. The dormant P-24 authorizer stays absent from every template (not enabled).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from careervp.rehome_map import REHOME_LOGICAL_IDS

# The two IMMUTABLE laws — these deployed logical ids must never move/replace.
RESTAPI_LOGICAL_ID = "CareerVpCrudDevCrudservicerestapi5E02FD49"
COGNITO_POOL_LOGICAL_ID = "CareerVpCrudDevCognitoUserPool42C0A4E4"
COGNITO_CLIENT_LOGICAL_ID = "CareerVpCrudDevCognitoUserPoolUserPoolClientFD4D0C15"
IMMUTABLE_LOGICAL_IDS = (
    RESTAPI_LOGICAL_ID,
    COGNITO_POOL_LOGICAL_ID,
    COGNITO_CLIENT_LOGICAL_ID,
)

# The P-24 custom authorizer is in rehome_map for id-stability bookkeeping, but it
# is DORMANT/latent: not deployed live, not synthesized while dormant, and is an
# additive CREATE (not a byte-stable import) if ever enabled. The source-of-truth
# test asserts it stays absent from EVERY template. It is therefore excluded from
# the "must be re-homed" set (G4) and guarded for dormancy separately (G6).
P24_AUTHORIZER_LOGICAL_ID = "CareerVpCrudDevCrudApiAuthorizerLambda"

# The real byte-stable imports (rehome_map minus the dormant P-24 authorizer).
REHOMED_IMPORT_IDS = tuple(
    lid for lid in REHOME_LOGICAL_IDS.values() if lid != P24_AUTHORIZER_LOGICAL_ID
)

PARENT_TEMPLATE = "CareerVpCrudDev.template.json"


def _resources(template_path: Path) -> dict[str, dict[str, object]]:
    data = json.loads(template_path.read_text())
    resources = data.get("Resources", {})
    if not isinstance(resources, dict):
        return {}
    return resources


def _find_crudfeatures_template(synth_dir: Path) -> Path:
    matches = sorted(synth_dir.glob("*CrudFeatures*.nested.template.json"))
    if not matches:
        raise FileNotFoundError(
            f"No *CrudFeatures*.nested.template.json in {synth_dir} — was it "
            f"synthesized with -c p26_rehome_features=true?"
        )
    return matches[0]


def gate(
    synth_on: Path,
    refactor_out: Path | None,
    parent_max: int,
    template_max: int,
) -> list[str]:
    """Return a list of failure messages (empty list == all gates passed)."""
    failures: list[str] = []

    parent = _resources(synth_on / PARENT_TEMPLATE)
    parent_count = len(parent)

    # Gate 1 — parent headroom.
    if parent_count >= parent_max:
        failures.append(
            f"[G1] parent CareerVpCrudDev has {parent_count} resources "
            f"(must be < {parent_max})"
        )
    else:
        print(f"[G1 OK] parent resources = {parent_count} (< {parent_max})")

    # Gate 2 — no template at/over the CloudFormation-adjacent ceiling.
    for tmpl in sorted(synth_on.glob("*.template.json")):
        count = len(_resources(tmpl))
        if count >= template_max:
            failures.append(
                f"[G2] template {tmpl.name} has {count} (>= {template_max})"
            )
    print(f"[G2 OK] no template >= {template_max}")

    crud = _resources(_find_crudfeatures_template(synth_on))

    # Gate 3 — IMMUTABLE laws.
    for lid in IMMUTABLE_LOGICAL_IDS:
        if lid not in parent:
            failures.append(
                f"[G3] IMMUTABLE {lid} missing from parent (moved/renamed?)"
            )
        if lid in crud:
            failures.append(
                f"[G3] IMMUTABLE {lid} present in CrudFeatures (MOVED — forbidden)"
            )
    if not any(f.startswith("[G3]") for f in failures):
        print(
            "[G3 OK] RestApi + Cognito pool/client stay in parent, absent from CrudFeatures"
        )

    # Gate 4 — the named resources are a byte-stable move (excludes dormant P-24).
    missing_in_crud = [lid for lid in REHOMED_IMPORT_IDS if lid not in crud]
    still_in_parent = [lid for lid in REHOMED_IMPORT_IDS if lid in parent]
    if missing_in_crud:
        failures.append(
            f"[G4] {len(missing_in_crud)} named ids NOT in CrudFeatures "
            f"(logical id not byte-stable): {missing_in_crud[:3]}..."
        )
    if still_in_parent:
        failures.append(
            f"[G4] {len(still_in_parent)} named ids STILL in parent "
            f"(not re-homed): {still_in_parent[:3]}..."
        )
    if not missing_in_crud and not still_in_parent:
        print(f"[G4 OK] all {len(REHOMED_IMPORT_IDS)} named ids re-homed byte-stable")

    # Gate 6 — the P-24 authorizer stays DORMANT (absent from every template).
    if P24_AUTHORIZER_LOGICAL_ID in parent:
        failures.append(
            f"[G6] P-24 authorizer {P24_AUTHORIZER_LOGICAL_ID} present in parent (not dormant)"
        )
    if P24_AUTHORIZER_LOGICAL_ID in crud:
        failures.append(
            f"[G6] P-24 authorizer {P24_AUTHORIZER_LOGICAL_ID} present in CrudFeatures (not dormant)"
        )
    if not any(f.startswith("[G6]") for f in failures):
        print(
            "[G6 OK] P-24 authorizer stays dormant (absent from parent + CrudFeatures)"
        )

    # Gate 5 — refactor dry-run log (optional; robust text scan).
    if refactor_out is not None:
        text = refactor_out.read_text()
        low = text.lower()
        if "refactor failed" in low:
            failures.append(
                "[G5] 'cdk refactor' log reports FAILURE — mapping not clean "
                "(normalize owner-tag/asset-hash drift; run from CI/runner context)"
            )
        for lid in IMMUTABLE_LOGICAL_IDS:
            if lid in text:
                failures.append(
                    f"[G5] IMMUTABLE {lid} appears in the refactor mapping (breach)"
                )
        for verb in (" destroy", " create", "replacement", "delete+create"):
            if verb in low:
                failures.append(
                    f"[G5] refactor log contains '{verb.strip()}' — a move-only "
                    f"refactor must show neither DELETE nor CREATE"
                )
        if not any(f.startswith("[G5]") for f in failures):
            print(
                "[G5 OK] refactor dry-run log: no failure, no immutable id, moves only"
            )
    else:
        print("[G5 SKIP] no --refactor-out supplied (synth-only gate)")

    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description="P-26 Job-1 refactor gate")
    ap.add_argument("--synth-on", required=True, type=Path, help="flag-ON cdk.out dir")
    ap.add_argument(
        "--refactor-out", type=Path, default=None, help="cdk refactor --dry-run log"
    )
    ap.add_argument("--parent-max", type=int, default=400)
    ap.add_argument("--template-max", type=int, default=500)
    args = ap.parse_args()

    failures = gate(
        args.synth_on, args.refactor_out, args.parent_max, args.template_max
    )
    if failures:
        print("\n=== P-26 REFACTOR GATE: FAIL — DO NOT EXECUTE ===", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        return 1
    print("\n=== P-26 REFACTOR GATE: PASS ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
