# Amendment Proposal — reconcile CV-tailoring omission coverage

> Emitted per scope-lock §0.3 after the complete 3.2-GREEN suite found
> affected existing coverage that the D-H4/P-01 spec brief did not inventory.
> This proposal awaits human validation. It does not edit the governing spec,
> either scope-lock twin, or either conflicting test.

| Field | Value |
|---|---|
| **clause_id** | `D-H4` / `AC-DH4-2` |
| **what changed** | The pinned RED requires an omitted `vpr_id` to return HTTP 400 before downstream work. Existing integration coverage requires the deployed `/cv-tailoring/generate` route to return HTTP 202 for `{cv_id, job_id}` with omitted `vpr_id` when the VPR dependency is generating. |
| **root defect** | The 3.2-SPEC RED brief omitted the affected-existing-test inventory. `RUNBOOK-RULES.md:301-303` requires newly discovered coverage to be flagged rather than silently reconciled. |
| **affected tests** | `src/backend/tests/unit/test_dh4_p01_canonical_artifact.py::test_dh4_cv_tailoring_preserves_vpr_id_null`; `src/backend/tests/integration/test_downstream_dependency_202.py::test_cv_tailoring_no_vpr_returns_202_not_500` |
| **affected public surface** | `POST /cv-tailoring/generate`; backend `CVTailoringRequest.vpr_id` already requires the key while accepting null. |
| **requires adversarial review?** | **Yes** — changing either assertion decides whether omission is invalid input or a dependency-generation request on the deployed route. |

## Plain-English problem

One locked test says a missing `vpr_id` must be rejected before any downstream
work. Another locked test says the deployed generation route must accept that
same omission and start the missing VPR dependency. Both cannot hold without a
special compatibility branch.

Fresh 2026-07-27 evidence:

```text
FAILED tests/integration/test_downstream_dependency_202.py::test_cv_tailoring_no_vpr_returns_202_not_500
E assert 400 == 202
```

The pinned D-H4 test is green with strict model validation, and the complete
backend suite otherwise reports this conflict plus the separately amended
interview-prep assertion. A route-specific, dependency-state-specific, or
test-double-specific exception would preserve omission compatibility and
contradict scope-lock v2.7.0/O-3, so none was added.

## Human decision required

Choose and record one contract:

1. Keep AC-DH4-2 as pinned and reconcile the existing dependency-generation
   integration test so callers send `vpr_id: null`; or
2. Amend D-H4/AC-DH4-2 to allow omission while a VPR dependency is generating.

If option 1 is approved, add the omitted existing-test inventory to the
governing spec and update the existing integration fixture in a separate,
visible test-only reconciliation. Keep the pinned RED test unchanged.
