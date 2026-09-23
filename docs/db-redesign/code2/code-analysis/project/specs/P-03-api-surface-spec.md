---
spec_id: P-03-API-SURFACE
title: "Map /api/* surface (verify staging-only)"
status: draft
owner: backend
tier: T1
scope_lock_clause: P-03
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "RED tests are TDD-first; inline RED-test descriptions (v1.3.0); pytest files written at IMPLEMENT in the real repo."
---

# Spec — P-03: Map the /api/* surface (verify staging-only)

- **Status:** SPEC ONLY — do **not** implement here. Apply under TDD in the redesign analysis wave (Track P, `P-*`).
- **Governs clause:** `P-03` (map /api/* surface, verify staging-only). Model/effort in the frontmatter above.
- **Code anchor:** `github.com/ymeirovich/careervp @ 0709bbd`. All file:line refs are at that commit.
- **Env note for the implementer:** backend requires Python **≥3.13** + `uv` (`src/backend/pyproject.toml`). Run tests via `uv run pytest` in `src/backend/`. CDK synth requires `uv sync` in `infra/` first.
- **TDD contract:** each check below lists the **RED test(s) to write and watch fail FIRST**, then the minimal GREEN verification. No production edit without a failing test first.
- **Oracle rule (scope-lock §0.2):** authoritative source is the CDK `route_map` in `infra/careervp/api_construct.py` plus handler definitions. The drifted swagger doc is NOT authoritative and MUST NOT be used to determine live routes.

---

## Problem Statement

The `/api/*` path prefix appears throughout the codebase in comments and historical code, but the CDK construct comments at `api_construct.py:924,974,1023,1184,1238,1751` all read:

> "Legacy `/api/*` routes removed. Canonical route registration lives in `_add_openapi_contract_routes()`."

This tells us the `/api/*` prefix was intentionally stripped from the live route surface during a migration, but the migration history was never machine-verified against:
1. The canonical `route_map` (`api_construct.py:2841–2912`) — which lists only bare paths (`/vpr/generate`, `/jobs`, etc.) with no `/api/` prefix.
2. The frontend call sites — whether any `src/frontend/` code still references `/api/` paths.
3. The CDK synth output — whether `/api/` appears as an actual API Gateway resource in the dev/prod stack.

Additionally, `infra/careervp/specs/_registry.yaml:29,96` records that **Phase 10** added "Temporary legacy `/api/*` compatibility during migration." This must be confirmed as either already removed or explicitly tagged as a known carry/drop item.

Until these three checks pass as automated assertions, P-03 is `partially_resolved` (scope-lock status). This spec closes it.

---

## Evidence

- **`infra/careervp/api_construct.py:2841–2912`** — The `route_map` list: 40 explicit routes, all with bare paths (`/health`, `/jobs`, `/vpr/generate`, …). Zero entries start with `/api/`. This is the canonical source of truth.
- **`infra/careervp/api_construct.py:924,974,1023,1184,1238,1751`** — Six Lambda integration methods each carry the comment "Legacy `/api/*` routes removed. Canonical route registration lives in `_add_openapi_contract_routes()`." These are the migration tombstones.
- **`infra/careervp/api_construct.py:102,112,151`** — Constructor comments still label Lambdas as "POST `/api/vpr`", "GET `/api/vpr/status/{job_id}`", "POST `/api/cv-tailoring`". These are **stale comments**, not live route registrations. The actual paths registered are `/vpr/generate`, `/vpr/{vprId}/status`, and `/cv-tailoring/generate` (via `route_map`).
- **`infra/careervp/specs/_registry.yaml:29,96`** — Phase 10 note: "Temporary legacy `/api/*` compatibility during migration." Status: unconfirmed whether this temporary compatibility was ever deployed and whether it has since been removed.
- **`infra/careervp/service_stack.py:101`** — Comment references the Next.js SSR `/api/errors` route. This is a Next.js internal route (server-side rendering), not an AWS API Gateway resource. Must be distinguished from CDK-managed routes.
- **`src/frontend/`** — Zero grep hits for `/api/` in frontend source (confirmed by grep returning no output). Frontend uses bare paths against the API base URL.
- **Scope-lock §0.2** — Oracle rule: CDK route_map + handlers are authoritative; swagger doc is not.

---

## Fix Plan

All steps are **verification only** — no production code changes. This clause closes by producing a machine-checkable route-surface ledger.

1. **Enumerate the canonical route surface from CDK `route_map`.**
   Read `infra/careervp/api_construct.py:2841–2912`. Extract each `(path, method, handler)` tuple. Produce a route-surface ledger (CSV or YAML) at `docs/db-redesign/code/code-analysis/redesign/evidence/route-surface-ledger.yaml`. Tag each route `carry` or `drop`. (All current `route_map` entries are `carry`; any `/api/`-prefixed entry found is `drop`.)

2. **Confirm zero frontend `/api/` calls.**
   Run `grep -r "/api/" src/frontend/` from the repo root. Expected: no output (or exit code 1). Document the result. If any hits are found, enumerate them and tag as `carry` (frontend still calls `/api/`) or `drop` (dead code / stale comment).

3. **Confirm `/api/*` is absent from CDK dev/prod synth.**
   Run `cdk synth` in `infra/` for the dev environment. Parse the synthesized CloudFormation template JSON (emitted to `cdk.out/`). Assert no `AWS::ApiGateway::Resource` has a `PathPart` value of `api` at the root level. If found, tag the resource as `carry` (intentional) or `drop` (migration residue).

4. **Resolve the Phase 10 legacy-compatibility note.**
   Inspect `infra/careervp/specs/_registry.yaml:29,96` and the Phase 10 infra entry ("Temporary legacy `/api/*` compatibility during migration"). Confirm whether this temporary compat was ever deployed (check git history or CDK diff). Mark as either `already_removed` or `pending_drop` in the ledger.

5. **Tag the stale constructor comments.**
   The comments at `api_construct.py:102,112,151` reference `/api/vpr`, `/api/vpr/status/{job_id}`, `/api/cv-tailoring` but these are not live routes. Tag them as `drop` (stale-comment-only) in the ledger. No code change required for this clause — the fix is a comment cleanup deferred to a later wave.

6. **Produce the spec-coverage-ledger row.**
   Append P-03's result to `docs/db-redesign/code/code-analysis/redesign/findings-register.md` with status `verified` or `finding` and the ledger path as evidence.

---

## Acceptance Criteria

**AC-P03-1** — *Given* the CDK `route_map` enumeration at `api_construct.py:2841–2912`, *When* we grep `src/frontend/` for `/api/`, *Then* zero frontend call sites reference `/api/*` paths (grep returns exit code 1 or empty stdout).

**AC-P03-2** — *Given* the dev/prod CDK synth output (CloudFormation JSON in `cdk.out/`), *When* we assert `/api/` resource presence, *Then* no `AWS::ApiGateway::Resource` with `PathPart: api` exists at the root level in either dev or prod synthesized stacks — confirming `/api/*` is absent from live deployments.

**AC-P03-3** — *Given* the complete route surface enumeration from `route_map` + `_register_feature_proxy` calls, *When* we tag each route `carry` or `drop`, *Then* every route has a tag, the ledger is machine-checkable (YAML or CSV), and zero routes carry the `/api/` prefix under the `carry` tag.

---

## RED Tests to Write First

### `test_frontend_has_no_api_star_calls`

```python
# tests/unit/infra/test_api_surface_p03.py
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[4]  # adjust depth to reach repo root

def test_frontend_has_no_api_star_calls():
    """AC-P03-1: No frontend source file calls /api/* paths."""
    result = subprocess.run(
        ["grep", "-r", "--include=*.ts", "--include=*.tsx", "--include=*.js",
         "/api/", str(REPO_ROOT / "src" / "frontend" / "src")],
        capture_output=True,
        text=True,
    )
    # grep returns exit code 1 when no matches found — that is the passing condition
    assert result.returncode == 1 or result.stdout.strip() == "", (
        f"Frontend contains /api/ call sites (AC-P03-1 violated):\n{result.stdout}"
    )
```

### `test_cdk_route_map_has_no_api_prefix`

```python
# tests/unit/infra/test_api_surface_p03.py (continued)
import ast
import re

API_CONSTRUCT = REPO_ROOT / "infra" / "careervp" / "api_construct.py"

def test_cdk_route_map_has_no_api_prefix():
    """AC-P03-3: No entry in the canonical route_map carries an /api/ prefix."""
    source = API_CONSTRUCT.read_text()
    # Extract the route_map list literal as raw text between the assignment and the for-loop
    match = re.search(
        r'route_map\s*:\s*list\[.*?\]\s*=\s*(\[.*?\])\s*for\s+path',
        source,
        re.DOTALL,
    )
    assert match, "Could not locate route_map list in api_construct.py"
    route_list_text = match.group(1)
    # Find all string literals that are route paths (first element of each tuple)
    paths = re.findall(r'"\s*(/[^"]+)"', route_list_text)
    api_paths = [p for p in paths if p.startswith("/api/")]
    assert api_paths == [], (
        f"route_map contains /api/-prefixed routes (AC-P03-3 violated): {api_paths}"
    )
```

### `test_cdk_synth_dev_has_no_api_gateway_resource_named_api`

```python
# tests/unit/infra/test_api_surface_p03.py (continued)
import json
import subprocess

CDK_OUT = REPO_ROOT / "infra" / "cdk.out"

def test_cdk_synth_dev_has_no_api_gateway_resource_named_api():
    """AC-P03-2: CDK dev synth produces no AWS::ApiGateway::Resource with PathPart 'api'."""
    # Run cdk synth if cdk.out is absent or stale; otherwise use cached output.
    if not CDK_OUT.exists():
        subprocess.run(
            ["python", "-m", "aws_cdk", "synth"],
            cwd=str(REPO_ROOT / "infra"),
            check=True,
        )
    # Collect all synthesized CloudFormation template files
    template_files = list(CDK_OUT.glob("**/*.template.json"))
    assert template_files, "No synthesized templates found in cdk.out/"
    violating_resources = []
    for template_file in template_files:
        template = json.loads(template_file.read_text())
        resources = template.get("Resources", {})
        for logical_id, resource in resources.items():
            if resource.get("Type") == "AWS::ApiGateway::Resource":
                path_part = resource.get("Properties", {}).get("PathPart", "")
                if path_part == "api":
                    violating_resources.append(
                        f"{template_file.name}::{logical_id} (PathPart={path_part!r})"
                    )
    assert violating_resources == [], (
        f"CDK synth contains /api/ API Gateway resources (AC-P03-2 violated):\n"
        + "\n".join(violating_resources)
    )
```

---

## Route Surface Ledger (Authoritative — from route_map + feature_proxies)

The following table is the machine-readable surface extracted from `api_construct.py:2829–2912` at commit `0709bbd`. All entries are tagged `carry`. No `/api/`-prefixed entry exists.

| Path | Method | Handler | Tag |
|------|--------|---------|-----|
| `/auth/{proxy+}` | ANY | `auth_api_func` | carry |
| `/users/{proxy+}` | ANY | `user_api_func` | carry |
| `/gap-analysis/{proxy+}` | ANY | `gap_api_func` | carry |
| `/billing/{proxy+}` | ANY | `billing_lambda` | carry |
| `/health` | GET | `health_api_func` | carry |
| `/users/me` | GET | `user_api_func` | carry |
| `/users/me` | PUT | `user_api_func` | carry |
| `/users/me/usage` | GET | `user_api_func` | carry |
| `/users/me/trial/reset` | POST | `user_api_func` | carry |
| `/users/me/cv` | POST | `cv_upload_func` | carry |
| `/users/me/cv` | GET | `user_api_func` | carry |
| `/users/me/subscription` | GET | `billing_lambda` | carry |
| `/jobs` | POST | `job_api_func` | carry |
| `/jobs` | GET | `job_api_func` | carry |
| `/jobs/{jobId}` | GET | `job_api_func` | carry |
| `/jobs/{jobId}/gap-questions` | POST | `gap_api_func` | carry |
| `/jobs/{jobId}/gap-questions` | GET | `gap_api_func` | carry |
| `/jobs/{jobId}/gap-responses` | POST | `gap_api_func` | carry |
| `/applications/{application_id}` | GET | `application_api_func` | carry |
| `/vpr/generate` | POST | `vpr_submit_func` | carry |
| `/vpr/{vprId}/status` | GET | `vpr_status_func` | carry |
| `/vpr/{vprId}/cancel` | POST | `vpr_status_func` | carry |
| `/vprs` | GET | `vpr_status_func` | carry |
| `/cv-tailoring/generate` | POST | `cv_tailoring_func` | carry |
| `/cv-tailoring/{cvTailoringId}/status` | GET | `cv_tailoring_func` | carry |
| `/cv-tailoring/{cvTailoringId}/cancel` | POST | `cv_tailoring_func` | carry |
| `/cv-tailoring/{cvTailoringId}` | DELETE | `cv_tailoring_func` | carry |
| `/cv-tailoring/{cvTailoringId}` | PATCH | `cv_tailoring_func` | carry |
| `/cv-tailorings` | GET | `cv_tailoring_func` | carry |
| `/cover-letter/generate` | POST | `cover_letter_api_func` | carry |
| `/cover-letter/{coverLetterId}/status` | GET | `cover_letter_status_func` | carry |
| `/cover-letter/{coverLetterId}/cancel` | POST | `cover_letter_status_func` | carry |
| `/cover-letter/{coverLetterId}` | PATCH | `cover_letter_status_func` | carry |
| `/cover-letters` | GET | `cover_letter_status_func` | carry |
| `/interview-prep/generate` | POST | `interview_prep_api_func` | carry |
| `/interview-prep/{interviewPrepId}/status` | GET | `interview_prep_status_func` | carry |
| `/interview-prep/{interviewPrepId}/cancel` | POST | `interview_prep_status_func` | carry |
| `/interview-preps` | GET | `interview_prep_status_func` | carry |
| `/company-research/{jobId}` | GET | `company_research_func` | carry |
| `/company-research/{jobId}/cancel` | POST | `company_research_func` | carry |
| `/company-research/fetch` | POST | `company_research_func` | carry |
| `/knowledge-base` | GET | `company_research_func` | carry |
| `/billing/webhook` | POST | `billing_lambda` | carry |
| `/jobs/{jobId}/artifacts/{moduleType}/export` | GET | `export_lambda` | carry |

**Stale comments tagged `drop` (comment-only, no live route registration):**

| Location | Stale Path Referenced | Tag | Actual Live Path |
|----------|-----------------------|-----|-----------------|
| `api_construct.py:102` | `POST /api/vpr` | drop (stale comment) | `POST /vpr/generate` |
| `api_construct.py:112` | `GET /api/vpr/status/{job_id}` | drop (stale comment) | `GET /vpr/{vprId}/status` |
| `api_construct.py:151` | `POST /api/cv-tailoring` | drop (stale comment) | `POST /cv-tailoring/generate` |

**Phase 10 legacy-compat item:**

| Registry Entry | Location | Tag | Resolution |
|----------------|----------|-----|-----------|
| "Temporary legacy `/api/*` compatibility during migration" | `_registry.yaml:29,96` | pending_drop | Confirm via `cdk synth` that no `/api/` `PathPart` resource exists; if absent from synth, mark `already_removed`. |

**Next.js SSR route (out of scope for CDK verification):**

| Source | Path | Tag | Note |
|--------|------|-----|------|
| `service_stack.py:101` | `/api/errors` (Next.js SSR) | carry (Next.js-internal) | Not an API Gateway resource; handled by Next.js runtime inside Amplify. Not subject to CDK route_map verification. |

---

## Done-When

- AC-P03-1..3 hold (all three RED tests pass green).
- The route-surface ledger in this spec (or its companion YAML at `evidence/route-surface-ledger.yaml`) is the machine-checkable record: every route is tagged `carry` or `drop`; zero routes carry the `/api/` prefix under `carry`.
- The Phase 10 legacy-compat item is resolved to `already_removed` or `pending_drop` with evidence from CDK synth.
- `ruff format . && ruff check --fix . && mypy careervp --strict` clean on any helper scripts added to `src/backend/scripts/`.
- Findings-register row for P-03 updated to `verified`.

---

## Sequencing

P-03 is a **read-only verification clause** (Track P, T1). It produces no code changes, only:
1. Three passing RED→GREEN test functions in `tests/unit/infra/test_api_surface_p03.py`.
2. The route-surface ledger (inline above; optionally mirrored to `evidence/route-surface-ledger.yaml`).
3. A `findings-register.md` row.

No downstream clauses block on P-03, but the route-surface ledger serves as input to any route-renaming or deprecation work in later waves.
