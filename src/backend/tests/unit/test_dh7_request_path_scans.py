"""D-H7 request-path Scan contracts — AC-DH7-1, pure-Python / mock half.

Spec: ``docs/db-redesign/code/code-analysis/project/specs/D-H7-request-path-scans-spec.md``
(pinned 2026-07-29 by step 3.3-SPEC).  Bet ``B-3-8`` in ``ISSUES.md`` settled **FALSE**:
there is no live request-path Scan that is 3.3's own to remove, so D-H7/3.3 ships as a
guard-rail + regression-test step with no read-path behaviour change.  **Every test in this
module is therefore a day-one GUARD, labelled as such with its reason.**  A guard that fails
when a Scan reappears is the deliverable; its green on day one is not evidence that the
clause is discharged.

This module holds the two halves of D-H7 that need nothing but the interpreter:

* ``test_dh7_no_scan_in_runtime_handlers_or_dal`` — Part A, the static AST source guard.
* ``test_dh7_subscription_lookup_uses_query`` — the subscription-lookup regression guard.

**Part B of ``test_dh7_no_scan_in_runtime_handlers_or_dal`` lives in
``tests/infrastructure/test_dh7_scan_iam_and_gsi_shape.py``** under the *same test name*,
because it needs a CDK synth.  Both halves belong to AC-DH7-1 per DP-2 (source **and** the
one explicit ``dynamodb:Scan`` grant); Part B is not a fourth D-H7 test and has no identity
of its own.  Selecting the D-H7 suite therefore requires **both** pytest roots::

    uv run pytest tests/unit tests/infrastructure -q -k "dh7"

``pytest tests/unit -k dh7`` alone is a false green — it silently skips Part B and the GSI
guard.

OUT OF SCOPE for 3.3, so that 3.3-GREEN inherits the boundary explicitly:

* ``dal/dynamo_dal_handler.py:800`` — the legacy cover-letter ``ValidationException`` scan
  fallback.  It *is* a request path and it *is* a real Scan, and it belongs to **3.5**
  (D-H9 legacy-path demolition; ``3.1-GREEN`` residue (c)).  It is allow-listed below, not
  removed.  Annexing it here is a rule-5 stop.
* ``dal/subscription_repository.py:415`` (``scan_active_subscriptions``) — retained on
  purpose by Wave-2 ``2.1-GREEN`` for ``BillingReconcileLambda``.
* ``scripts/cr_migration_backfill.py:261`` — offline; excluded by directory, and deleted at
  3.5.
* The **22** implicit ``grant_read_data`` / ``grant_read_write_data`` Scan grants in
  ``infra/careervp/api_construct.py`` — **3.4's**, per DP-2.  Nothing here asserts on them.
* The three residues ``3.1-GREEN`` recorded, and everything ``3.2-GREEN`` listed with a
  named owner.
* Auth / trial / user-pool keying (Wave-6 D-H8) and the D-M god-class split (3.4).
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

BACKEND_ROOT = Path(__file__).resolve().parents[2]

# ── Part A: scanned scope ─────────────────────────────────────────────────────────────────
# Exactly these three directories, recursively, ``*.py`` only — 105 files live (handlers 43,
# dal 17, logic 45), re-counted 2026-07-30.  Every exclusion is by decision, not convenience:
# ``careervp/models``, ``careervp/validation``, ``careervp/payment_providers`` and
# ``careervp/infrastructure`` hold no DynamoDB call sites and sit outside the AC's
# "handlers/repositories" wording; ``src/backend/scripts`` is offline (Fix Plan item 3
# allow-lists offline scripts, and excluding the directory is what that means in practice);
# ``src/backend/tests`` legitimately calls ``.scan()`` on doubles and on moto tables
# (e.g. ``test_p14_p15_billing_idempotency.py:191``); ``.build/`` is a generated stale copy of
# every source file and would double every count.
SCANNED_DIRS: tuple[str, ...] = (
    'careervp/handlers',
    'careervp/dal',
    'careervp/logic',
)

# ── Part A: the allow-list ────────────────────────────────────────────────────────────────
# ENUMERATED SITE BY SITE with the dated decision that owns it.  Exactly two entries.  A
# directory wildcard is forbidden here: a wildcard over ``dal/`` would silently absorb any
# future Scan added to any of its 17 files.
#
# Keys are ``(relative_path, enclosing_function_name)`` and never line numbers, so an
# unrelated edit above the site cannot break the build and invite the next session to "fix"
# the test.
SCAN_BASELINE: Mapping[tuple[str, str], str] = {
    (
        'careervp/dal/subscription_repository.py',
        'scan_active_subscriptions',
    ): (
        "Wave-2 2.1-GREEN ledger row — 'preserve scan_active_subscriptions and "
        "BillingReconcileLambda Scan access; money path and reconcile are separate Lambdas.' "
        'Reconcile-only, not a request path; enforced by the reconciliation_service.py:14 '
        'docstring prohibition.'
    ),
    (
        'careervp/dal/dynamo_dal_handler.py',
        'legacy_read_cover_letter',
    ): (
        '3.5 (D-H9 legacy-path demolition) — the legacy cover-letter family recorded as '
        "3.1-GREEN residue (c).  Allow-listed ONLY until 3.5 deletes it; not 3.3-GREEN's to "
        "remove.  NOTE the spec's allow-list table names the enclosing function "
        '_legacy_read_cover_letter_by_scan; live, that function (dynamo_dal_handler.py:663) '
        'issues no Scan at all and the real Scan at :800 sits in legacy_read_cover_letter '
        '(def at :782).  The site the spec identifies is unambiguous — same file, same line, '
        'same verbatim scan expression — so the key uses the live enclosing name, which is '
        'also the name ISSUES.md B-3-8 records.  Flagged for human review; see the 3.3-RED '
        'ledger row.'
    ),
}

# Files the guard must contribute ZERO sites for.  These are the live false-positive traps a
# ``".scan("`` regex fires on and AST call-matching cannot (Evidence E-7): the
# ``'…using list-scan fallback (Phase A)'`` log string plus its docstring at
# ``cover_letter_handler.py:1155-1171`` (a Query followed by in-Python filtering), and
# ``ScanIndexForward=False`` at ``jobs_repository.py:159`` (a Query keyword argument).
NO_SITE_FILES: tuple[str, ...] = (
    'careervp/handlers/cover_letter_handler.py',
    'careervp/dal/jobs_repository.py',
)


@dataclass(frozen=True)
class ScanSite:
    """One statically detected Scan-shaped site."""

    path: str
    function: str
    line: int
    form: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.path, self.function)


def _string_arg(node: ast.Call, index: int) -> str | None:
    if len(node.args) <= index:
        return None
    arg = node.args[index]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return None


class _ScanSiteVisitor(ast.NodeVisitor):
    """Flag the four Scan-shaped call forms the spec pins, tracking the enclosing function."""

    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        self.sites: list[ScanSite] = []
        self._function_stack: list[str] = []
        # Attribute nodes occupying a ``Call.func`` position, so form 2 does not double-report
        # what form 1 already caught.
        self._call_func_ids: set[int] = set()

    @property
    def _enclosing(self) -> str:
        return self._function_stack[-1] if self._function_stack else '<module>'

    def _record(self, node: ast.AST, form: str) -> None:
        self.sites.append(
            ScanSite(
                path=self.rel_path,
                function=self._enclosing,
                line=getattr(node, 'lineno', 0),
                form=form,
            )
        )

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        if isinstance(func, ast.Attribute):
            self._call_func_ids.add(id(func))
            if func.attr == 'scan':
                # Form 1: any receiver — table.scan(...), self._table.scan(...),
                # dynamodb.Table(n).scan(...).
                self._record(node, 'form-1 <receiver>.scan(...)')
            elif func.attr == 'get_paginator' and _string_arg(node, 0) == 'scan':
                # Form 4: the boto3 low-level paginator route.
                self._record(node, "form-4 get_paginator('scan')")
        elif isinstance(func, ast.Name) and func.id == 'getattr' and _string_arg(node, 1) == 'scan':
            # Form 3: getattr(table, 'scan')(...).
            self._record(node, "form-3 getattr(<receiver>, 'scan')")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        if node.attr == 'scan' and id(node) not in self._call_func_ids:
            # Form 2: a bare reference — ``fn = table.scan`` followed by a later ``fn(...)``,
            # which form 1 alone misses.
            self._record(node, 'form-2 bare .scan attribute reference')
        self.generic_visit(node)


def find_scan_sites(roots: Iterable[Path], base: Path) -> list[ScanSite]:
    """Return every statically detectable Scan-shaped site under ``roots``.

    Takes its input as a parameter so the detector is provable against a poisoned tree
    without touching a single implementation file — a guard that can only run against the
    real source tree is a guard nobody can watch fail.

    Detection is **AST, not regex**.  A ``".scan("`` regex misses forms 2-4 entirely and
    false-positives on live code (``ScanIndexForward=False``; the ``'…list-scan fallback…'``
    log string).  AST matches call structure, so comments, docstrings, log strings and
    keyword arguments cannot match.

    KNOWN LIMITS — deliberate accepted gaps, recorded so no reader mistakes this for a proof:

    * **Dynamic dispatch with a computed name** (``getattr(table, method_name)`` where
      ``method_name`` is a variable, or ``eval``/``exec``) is undetectable by static
      analysis.  Live-verified zero at pinning.
    * **Differently-named wrappers are out of reach by design.**
      ``handlers/artifact_cleanup_handler.py:188`` calls
      ``deps.jobs_repo.scan_by_status(...)``; ``attr == 'scan_by_status' != 'scan'``, so this
      detector does not flag it — correctly, because **no Scan is issued at all**: the method
      does not exist anywhere in the repo, ``deps`` is typed ``Any`` so ``mypy --strict``
      cannot see it, and the ``AttributeError`` is swallowed by
      ``except Exception: return []`` (Evidence E-6).  Matching on a ``scan_*`` prefix was
      **rejected**: it would fail on day one against a site that issues no Scan, on a
      scheduled reaper rather than a request path, whose underlying bug is not 3.3's to fix
      and is separately flagged for human review.  If a future session implements
      ``scan_by_status`` on ``JobsRepository`` using ``table.scan(...)``, that lands in
      ``dal/`` and this guard catches it there.
    * **Cross-module aliasing** (``from x import scan as s``) is not modelled; no such
      imports exist live.
    * The guard proves nothing about **runtime** behaviour — that is AC-DH7-1's IAM half
      (Part B) and the clause's ``verification: integration``, which a unit suite does not
      discharge (Evidence E-8).
    """
    sites: list[ScanSite] = []
    for root in roots:
        for path in sorted(root.rglob('*.py')):
            visitor = _ScanSiteVisitor(path.relative_to(base).as_posix())
            visitor.visit(ast.parse(path.read_text(encoding='utf-8')))
            sites.extend(visitor.sites)
    return sites


def test_dh7_no_scan_in_runtime_handlers_or_dal() -> None:
    """AC-DH7-1 (Part A): no Scan call survives in handlers/dal/logic outside the allow-list.

    **GUARD — frozen-baseline ratchet, green on day one by construction.**  Reason: ``B-3-8``
    settled FALSE, so no request-path Scan is 3.3's to remove; both surviving sites are owned
    by decisions that already exist (Wave-2 ``2.1-GREEN`` and 3.5).  Its value is that a
    *newly added* Scan fails here.

    The assertion is a **RATCHET** (``found ⊆ BASELINE`` — may shrink, never grow), **not**
    ``assert len(found) == 0``.  An absolute zero-occurrences assertion over ``dal/`` is
    unsatisfiable by anything 3.3 is scoped to do: it would require removing
    ``subscription_repository.py:415``, which Wave-2 ``2.1-GREEN`` deliberately retained, or
    removing ``dynamo_dal_handler.py:800``, which is 3.5's work — a false green and a rule-5
    stop respectively.  **Shrink must not fail:** when 3.5 deletes
    ``dynamo_dal_handler.py:800``, this test must still pass unedited, which is why baseline
    resolvability is asserted at *file* granularity and not per function.

    Part B of this test — the one explicit ``dynamodb:Scan`` IAM grant, and the only
    red-today assertion in all of 3.3 — is in
    ``tests/infrastructure/test_dh7_scan_iam_and_gsi_shape.py`` under this same name.
    """
    roots = [BACKEND_ROOT / rel for rel in SCANNED_DIRS]
    missing_roots = [str(root) for root in roots if not root.is_dir()]
    assert not missing_roots, f'AC-DH7-1: scanned scope is not resolvable: {missing_roots}'

    scanned_files = sorted(path for root in roots for path in root.rglob('*.py'))
    assert scanned_files, 'AC-DH7-1: the scanned scope matched zero files; this guard would pass vacuously'

    # The baseline may not rot into a no-op: every allow-listed FILE must still exist.  The
    # enclosing function is deliberately NOT required to exist, so 3.5 deleting its site is a
    # clean shrink rather than a build break.
    unresolvable = sorted(rel_path for (rel_path, _function) in SCAN_BASELINE if not (BACKEND_ROOT / rel_path).is_file())
    assert not unresolvable, (
        f'AC-DH7-1: allow-listed files no longer exist and the baseline has rotted into a no-op: {unresolvable}. '
        'Remove the stale entry in the same change that removed the file.'
    )

    sites = find_scan_sites(roots, BACKEND_ROOT)
    unlisted = sorted({site.key for site in sites} - set(SCAN_BASELINE))
    offenders = sorted(f'{site.path}::{site.function} (line {site.line}, {site.form})' for site in sites if site.key in unlisted)
    assert not unlisted, (
        f'AC-DH7-1: DynamoDB Scan call site(s) outside the D-H7 allow-list: {offenders}. '
        'Replace the Scan with a keyed Query/GSI lookup, or add it to the D-H7 baseline only with a dated decision that owns it.'
    )

    # Positive proof that AST matching does not fire on the live false-positive traps a regex
    # would flag (Evidence E-7) — the reason this detector is AST-based at all.
    for rel_path in NO_SITE_FILES:
        contributed = sorted(f'{site.function} (line {site.line}, {site.form})' for site in sites if site.path == rel_path)
        assert not contributed, (
            f'AC-DH7-1: {rel_path} must contribute zero Scan sites (it has no Scan; only Query + "list-scan" naming), got {contributed}'
        )


def test_dh7_subscription_lookup_uses_query() -> None:
    """AC-DH7-1: the customer-id subscription lookup queries the GSI and never scans.

    **GUARD — regression guard, DUPLICATE BY DESIGN, green on day one.**  Be plain about what
    this adds, because the coverage already exists:
    ``tests/unit/test_p14_p15_billing_idempotency.py:198-220``
    (``test_p15_billing_lookup_uses_query_not_scan``, **AC-P15-1**) already asserts every
    substantive fact about this path — index name, partition-key name, equality value and
    ``scan.assert_not_called()``.  What this test adds is **not new coverage**; it is **AC
    ownership**: AC-DH7-1 must be independently verifiable from D-H7's own module, so that
    re-scoping or relocating the P-15 billing test cannot silently remove D-H7's evidence.
    It is not a fix, and it is not a redundant copy to delete.

    The stimulus deliberately mirrors the P-15 test so the two cannot drift apart.

    ``scan.assert_not_called()`` is **bounded to this single
    ``get_subscription_by_customer_id`` invocation** and asserts nothing whatever about
    ``scan_active_subscriptions`` — neither its behaviour, nor its existence, nor its call
    count.  That Scan is **deliberately retained** by Wave-2 ``2.1-GREEN`` for
    ``BillingReconcileLambda``; a repository-level "never scans" assertion here would
    silently break the reconcile path Wave 2 explicitly chose to keep.  The retention fact
    lives in Evidence E-1 and in Part A's allow-list, which is its correct home.
    """
    try:
        from careervp.dal.subscription_repository import CUSTOMER_ID_INDEX_NAME, SubscriptionRepository
    except ImportError as exc:  # pragma: no cover - defended, never skipped
        raise AssertionError(
            f'AC-DH7-1: SubscriptionRepository/CUSTOMER_ID_INDEX_NAME not available at careervp.dal.subscription_repository ({exc})'
        ) from exc

    users_table_name = 'careervp-users-table-test'
    idempotency_table_name = 'careervp-idempotency-table-test'

    dynamodb = MagicMock()
    users_table = MagicMock()
    idempotency_table = MagicMock()
    dynamodb.Table.side_effect = lambda name: idempotency_table if name == idempotency_table_name else users_table
    users_table.query.return_value = {'Items': []}

    repository = SubscriptionRepository(
        table_name=users_table_name,
        idempotency_table_name=idempotency_table_name,
        dynamodb_resource=dynamodb,
    )

    repository.get_subscription_by_customer_id('cus_dh7_001')

    users_table.query.assert_called_once()
    query: dict[str, Any] = users_table.query.call_args.kwargs
    assert query['IndexName'] == CUSTOMER_ID_INDEX_NAME == 'customer-id-index', (
        f'AC-DH7-1 requires the customer-id-index, got {query.get("IndexName")!r}'
    )

    expression = query['KeyConditionExpression'].get_expression()
    partition_key, expected_customer_id = expression['values']
    assert partition_key.name == 'customer_id', f'AC-DH7-1 requires customer_id as the GSI partition key, got {partition_key.name!r}'
    assert expected_customer_id == 'cus_dh7_001', f'AC-DH7-1 requires an equality query on the provider customer id, got {expected_customer_id!r}'

    users_table.scan.assert_not_called()
