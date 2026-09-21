"""table_map.py — every table env var name, the physical table it resolves to,
and who reads or writes it.

Why this exists
----------------
"Four table env vars, three aliasing one physical table" (see
docs/handoff/2026-09-19-PRODUCTION-PROGRAM.md, W2) is the class of defect where
one Lambda writes an artifact to one table and another Lambda — or another
code path in the *same* Lambda — reads it back from a different one. It
cannot be found by reading code linearly; a comment in api_construct.py
already records one near-miss of exactly this shape. This tool builds the
env-var -> physical-table map mechanically so the next one is a diff, not a
production incident.

How resolution works (no guessing — see `_client-side callers` below)
--------------------------------------------------------------------------
1. `infra/careervp/api_db_construct.py`'s `ApiDbConstruct.__init__` assigns
   `self.<attr>: dynamodb.TableV2 = self._build_<x>(...)`; each `_build_<x>`
   method's own body names the physical table via
   `self.naming.table_name(constants.<CONST>)`. That gives attr -> constant.
   A bare `self.<a> = self.<b>` (e.g. `self.db = self.users_table`) is an
   alias and inherits `b`'s constant.
2. `infra/careervp/api_construct.py` builds one more table directly
   (`_build_llm_cache_table`), discovered the same way, plus its own
   `self.<attr> = self._build_llm_cache_table(...)` assignment.
3. Every dict entry across infra/careervp/*.py of shape `"<NAME>": <expr>` or
   `constants.<NAME>_ENV: <expr>` (the latter resolved via constants.py's own
   `<NAME>_ENV = "<NAME>"` literal) where `<expr>` is `<name>.table_name` or
   `self.api_db.<name>.table_name` is an env-var assignment. `<name>` is
   resolved against the attr map from steps 1-2 directly — this codebase
   names its Lambda-builder parameters after the api_db attribute they were
   seeded from (`jobs_table=self.api_db.jobs_table`, etc; verified by
   inspection, not assumed), so a bare-name match is precise here, not a
   heuristic that happens to mostly work.
4. Anything that does not resolve is reported UNRESOLVED, never silently
   skipped or guessed — the same rule preflight.py follows.

Consumer side
--------------
Every `os.environ.get('<NAME>')` / `os.environ['<NAME>']` under
src/backend/careervp/ naming something containing `TABLE` is a consumer.
Cross-referencing producers (CDK) against consumers (backend) surfaces:
    - a name the backend reads that CDK never sets on any Lambda (a fallback
      that can never fire, or a stale rename)
    - a name CDK sets that nothing in the backend ever reads (dead env var)
    - a name that resolves to more than one physical table depending on which
      Lambda sets it (reported, not judged — DYNAMODB_TABLE_NAME is a generic
      name reused per-Lambda by design; a name that is NOT meant to be
      generic doing this is the actual bug shape to look for)

What this does not attempt
------------------------------
Whether a *specific artifact type* (VPR, gap, cover letter, ...) writes to a
table its own reader expects is a semantic judgement this tool does not make;
it reports which env vars (and therefore which physical tables) each DAL
module touches so a human can make that call. See docs/DEAD-CODE.md for one
instance already run down by hand.

Usage
-----
    uv run python scripts/table_map.py
    uv run python scripts/table_map.py --json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_stamp import REPO_ROOT, write_proof  # noqa: E402

INFRA_ROOT: Final[Path] = REPO_ROOT / 'infra' / 'careervp'
API_DB_CONSTRUCT: Final[Path] = INFRA_ROOT / 'api_db_construct.py'
CONSTANTS_PY: Final[Path] = INFRA_ROOT / 'constants.py'
BACKEND_ROOT: Final[Path] = REPO_ROOT / 'src' / 'backend' / 'careervp'
EXCLUDE_PARTS: Final[frozenset[str]] = frozenset({'.build', 'cdk.out', '__pycache__', '.venv'})

ENV_READ_RE: Final[re.Pattern[str]] = re.compile(r"os\.environ(?:\.get)?\s*(?:\[|\()\s*['\"]([A-Z0-9_]*TABLE[A-Z0-9_]*)['\"]")
DYNAMO_WRITE_OPS: Final[frozenset[str]] = frozenset({'put_item', 'update_item', 'delete_item', 'transact_write_items', 'batch_write_item'})
DYNAMO_READ_OPS: Final[frozenset[str]] = frozenset({'get_item', 'query', 'scan', 'batch_get_item', 'transact_get_items'})


def _iter_py(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in sorted(root.rglob('*.py')) if not any(part in EXCLUDE_PARTS for part in p.parts)]


@dataclass
class PhysicalTable:
    attr: str
    constant: str
    builder: str


def _constant_ref(node: ast.AST) -> str | None:
    """`constants.SOMETHING` -> 'SOMETHING'."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'constants':
        return node.attr
    return None


def _self_call_func(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'self':
        return node.func.attr
    return None


def _self_target_attr(target: ast.AST) -> str | None:
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
        return target.attr
    return None


def _attr_assignment(node: ast.Assign | ast.AnnAssign) -> tuple[str, ast.expr] | None:
    """`self.<attr> = <value>` (or annotated) -> (attr, value); anything else -> None."""
    if node.value is None:
        return None
    target = node.targets[0] if isinstance(node, ast.Assign) else node.target
    attr = _self_target_attr(target)
    if attr is None:
        return None
    return attr, node.value


def _direct_alias_attr(value: ast.expr) -> str | None:
    """`self.<other>` (no call) -> '<other>'."""
    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id == 'self':
        return value.attr
    return None


def _collect_builder_assignments(
    tree: ast.Module, attr_to_builder: dict[str, str], aliases: dict[str, str], builder_bodies: dict[str, ast.FunctionDef]
) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            builder_bodies[node.name] = node
            continue
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        found = _attr_assignment(node)
        if found is None:
            continue
        attr, value = found
        builder = _self_call_func(value)
        if builder:
            attr_to_builder[attr] = builder
            continue
        other_attr = _direct_alias_attr(value)
        if other_attr:
            aliases[attr] = other_attr


def _keyword_alias_target(value: ast.expr) -> str | None:
    """`self.api_db.<attr>` or `self.<attr>` passed as a keyword value -> '<attr>'."""
    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Attribute) and value.value.attr == 'api_db':
        return value.attr
    if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id == 'self':
        return value.attr
    return None


def _collect_keyword_aliases(tree: ast.Module, aliases: dict[str, str]) -> None:
    """`_add_x_lambda(..., idempotency_table=self.api_db.idempotency_db, ...)` binds the parameter
    name `idempotency_table` to attr `idempotency_db` — a real rename, not a bare-name match, and
    the one case in this codebase where the two differ (verified by inspection)."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg is None:
                continue
            target_attr = _keyword_alias_target(kw.value)
            if target_attr:
                aliases.setdefault(kw.arg, target_attr)


def _builder_to_constant(builder_bodies: dict[str, ast.FunctionDef]) -> dict[str, str]:
    builder_to_constant: dict[str, str] = {}
    for name, fn in builder_bodies.items():
        for sub in ast.walk(fn):
            const = _constant_ref(sub)
            if const and const.endswith('_TABLE_NAME'):
                builder_to_constant[name] = const
                break
    return builder_to_constant


def _resolve_aliases(tables: dict[str, PhysicalTable], aliases: dict[str, str]) -> None:
    changed = True
    while changed:
        changed = False
        for alias_attr, target_attr in aliases.items():
            if alias_attr in tables or target_attr not in tables:
                continue
            tables[alias_attr] = PhysicalTable(attr=alias_attr, constant=tables[target_attr].constant, builder=f'alias:{target_attr}')
            changed = True


def discover_physical_tables(*sources: tuple[str, Path]) -> dict[str, PhysicalTable]:
    """Across one or more (source_text, path) infra files: attr -> PhysicalTable."""
    attr_to_builder: dict[str, str] = {}
    aliases: dict[str, str] = {}
    builder_bodies: dict[str, ast.FunctionDef] = {}

    for source, _path in sources:
        _collect_builder_assignments(ast.parse(source), attr_to_builder, aliases, builder_bodies)
    for source, _path in sources:
        _collect_keyword_aliases(ast.parse(source), aliases)

    builder_to_constant = _builder_to_constant(builder_bodies)
    tables: dict[str, PhysicalTable] = {}
    for attr, builder in attr_to_builder.items():
        constant = builder_to_constant.get(builder)
        if constant:
            tables[attr] = PhysicalTable(attr=attr, constant=constant, builder=builder)

    _resolve_aliases(tables, aliases)
    return tables


def discover_env_constants(source: str) -> dict[str, str]:
    """`NAME_ENV = "NAME"` module-level string constants in constants.py -> {NAME_ENV: NAME}."""
    tree = ast.parse(source)
    out: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                out[node.targets[0].id] = node.value.value
    return out


@dataclass
class EnvAssignment:
    env_var: str
    resolved_constant: str | None
    resolved_attr: str | None
    file: str
    line: int


def _dict_key_env_name(key: ast.expr, env_constants: dict[str, str]) -> str | None:
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        return key.value
    const = _constant_ref(key)
    if const:
        return env_constants.get(const, const)
    return None


def _env_assignment_from_entry(
    key: ast.expr, value: ast.expr, env_name: str, tables: dict[str, PhysicalTable], path: Path, unresolved: list[str]
) -> EnvAssignment:
    rel = path.relative_to(REPO_ROOT)
    line = getattr(key, 'lineno', 0)
    attr = _resolve_table_name_expr(value)
    if attr is None:
        unresolved.append(f'{rel}:{line}: {env_name!r} -> {ast.dump(value)[:80]}')
        return EnvAssignment(env_var=env_name, resolved_constant=None, resolved_attr=None, file=str(rel), line=line)

    table = tables.get(attr)
    if table is None:
        unresolved.append(f'{rel}:{line}: {env_name!r} -> attr {attr!r} is not a known table attr')
    return EnvAssignment(env_var=env_name, resolved_constant=table.constant if table else None, resolved_attr=attr, file=str(rel), line=line)


def discover_env_assignments(
    sources: list[tuple[str, Path]], tables: dict[str, PhysicalTable], env_constants: dict[str, str]
) -> tuple[list[EnvAssignment], list[str]]:
    assignments: list[EnvAssignment] = []
    unresolved: list[str] = []

    for source, path in sources:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values, strict=True):
                if key is None:
                    continue
                env_name = _dict_key_env_name(key, env_constants)
                if env_name is None or 'TABLE' not in env_name:
                    continue
                assignments.append(_env_assignment_from_entry(key, value, env_name, tables, path, unresolved))

    return assignments, unresolved


def _resolve_table_name_expr(node: ast.AST) -> str | None:
    """`<name>.table_name` or `self.api_db.<name>.table_name` -> '<name>'."""
    if not (isinstance(node, ast.Attribute) and node.attr == 'table_name'):
        return None
    base = node.value
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        if isinstance(base.value, ast.Attribute) and base.value.attr == 'api_db':
            return base.attr
        if isinstance(base.value, ast.Name) and base.value.id == 'self':
            return base.attr
    return None


@dataclass
class BackendConsumer:
    module: str
    env_vars: list[str]
    read_ops: int
    write_ops: int


ENV_READ_INDIRECT_RE: Final[re.Pattern[str]] = re.compile(r'os\.environ(?:\.get)?\s*(?:\[|\()\s*([A-Z][A-Z0-9_]*)\s*[,)\]]')


def _discover_string_constants(paths: list[Path]) -> dict[str, str]:
    """Best-effort, cross-file: `NAME = 'literal'` at module level, anywhere in the tree.

    Consumers sometimes read a table env var through an imported name
    (`os.environ.get(IDENTITY_MAP_TABLE_ENV)`) instead of the literal string.
    This is a heuristic, not a full import resolution — good enough to stop a
    same-named constant defined once from reading as "never consumed".
    """
    out: dict[str, str] = {}
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding='utf-8', errors='ignore'))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    out.setdefault(node.targets[0].id, node.value.value)
    return out


def discover_backend_consumers() -> list[BackendConsumer]:
    paths = _iter_py(BACKEND_ROOT)
    string_constants = _discover_string_constants(paths)

    consumers: list[BackendConsumer] = []
    for path in paths:
        text = path.read_text(encoding='utf-8', errors='ignore')
        env_vars = set(ENV_READ_RE.findall(text))
        for name in ENV_READ_INDIRECT_RE.findall(text):
            resolved = string_constants.get(name)
            if resolved and 'TABLE' in resolved:
                env_vars.add(resolved)
        if not env_vars:
            continue
        read_ops = sum(len(re.findall(rf'\.{op}\s*\(', text)) for op in DYNAMO_READ_OPS)
        write_ops = sum(len(re.findall(rf'\.{op}\s*\(', text)) for op in DYNAMO_WRITE_OPS)
        consumers.append(BackendConsumer(module=str(path.relative_to(REPO_ROOT)), env_vars=sorted(env_vars), read_ops=read_ops, write_ops=write_ops))
    return consumers


@dataclass
class Report:
    physical_tables: dict[str, str]  # attr -> constant
    alias_groups: dict[str, list[str]]  # constant -> sorted env var names ever bound to it
    inconsistent_env_vars: dict[str, list[str]]  # env var -> sorted distinct constants it resolves to (len > 1)
    produced_not_consumed: list[str]
    produced_not_consumed_weak: list[
        str
    ]  # mentioned as a string somewhere, but not via a pattern this tool follows — needs a human look, not a guess
    consumed_not_produced: list[str]
    consumers: list[BackendConsumer]
    unresolved: list[str]


def build_report() -> Report:
    db_source = API_DB_CONSTRUCT.read_text(encoding='utf-8')
    api_source = (INFRA_ROOT / 'api_construct.py').read_text(encoding='utf-8')
    constants_source = CONSTANTS_PY.read_text(encoding='utf-8')

    tables = discover_physical_tables((db_source, API_DB_CONSTRUCT), (api_source, INFRA_ROOT / 'api_construct.py'))
    env_constants = discover_env_constants(constants_source)

    nested_stacks = [p for p in INFRA_ROOT.glob('*.py') if 'nested_stack' in p.name]
    sources = [(api_source, INFRA_ROOT / 'api_construct.py')] + [(p.read_text(encoding='utf-8'), p) for p in nested_stacks]
    assignments, unresolved = discover_env_assignments(sources, tables, env_constants)

    alias_groups: dict[str, set[str]] = {}
    env_to_constants: dict[str, set[str]] = {}
    produced_env_vars: set[str] = set()
    for a in assignments:
        produced_env_vars.add(a.env_var)
        if a.resolved_constant:
            alias_groups.setdefault(a.resolved_constant, set()).add(a.env_var)
            env_to_constants.setdefault(a.env_var, set()).add(a.resolved_constant)

    inconsistent = {k: sorted(v) for k, v in env_to_constants.items() if len(v) > 1}

    consumers = discover_backend_consumers()
    consumed_env_vars: set[str] = set()
    for c in consumers:
        consumed_env_vars.update(c.env_vars)

    produced_not_consumed_candidates = sorted(produced_env_vars - consumed_env_vars)
    consumed_not_produced = sorted(consumed_env_vars - produced_env_vars)

    # Backstop for indirection this tool's AST/regex passes cannot follow (a
    # candidate name forwarded through *args to a shared "try these env keys
    # in order" helper, for one real example in this codebase): does the name
    # appear as a quoted string ANYWHERE in the backend tree at all? A name
    # that fails even this loose a check is not a false negative of a
    # narrower pattern — it is not typed anywhere in the backend.
    all_text = '\n'.join(p.read_text(encoding='utf-8', errors='ignore') for p in _iter_py(BACKEND_ROOT))
    produced_not_consumed: list[str] = []
    produced_not_consumed_weak: list[str] = []
    for name in produced_not_consumed_candidates:
        if re.search(rf"['\"]{re.escape(name)}['\"]", all_text):
            produced_not_consumed_weak.append(name)
        else:
            produced_not_consumed.append(name)

    return Report(
        physical_tables={attr: t.constant for attr, t in sorted(tables.items())},
        alias_groups={k: sorted(v) for k, v in sorted(alias_groups.items())},
        inconsistent_env_vars=inconsistent,
        produced_not_consumed=produced_not_consumed,
        produced_not_consumed_weak=produced_not_consumed_weak,
        consumed_not_produced=consumed_not_produced,
        consumers=consumers,
        unresolved=sorted(set(unresolved)),
    )


def _render_physical_tables(report: Report) -> list[str]:
    lines = [f'{len(report.physical_tables)} physical tables (by attribute):']
    for attr, constant in report.physical_tables.items():
        lines.append(f'  - {attr:30s} -> {constant}')
    return lines


def _render_alias_groups(report: Report) -> list[str]:
    lines = [f'alias groups (N env var names -> 1 physical table), {len(report.alias_groups)} tables have >=1 name bound:']
    for constant, names in report.alias_groups.items():
        marker = '  *** many names ***' if len(names) > 2 else ''
        lines.append(f'  - {constant}: {", ".join(names)}{marker}')
    return lines


def _render_inconsistent(report: Report) -> list[str]:
    if not report.inconsistent_env_vars:
        return ['no env var name resolves to more than one physical table.']
    lines = [f'SAME env var name resolves to DIFFERENT physical tables depending on which Lambda sets it ({len(report.inconsistent_env_vars)}):']
    for name, constants in report.inconsistent_env_vars.items():
        lines.append(f'  - {name}: {", ".join(constants)}')
    lines.append('  (may be by design for a generic name like DYNAMODB_TABLE_NAME — verify per-Lambda before treating as a bug)')
    return lines


def _render_producer_consumer_gaps(report: Report) -> list[str]:
    lines = [f'CDK sets it, nothing in src/backend/careervp reads it — not even as a quoted string ({len(report.produced_not_consumed)}):']
    lines.extend(f'  - {name}' for name in report.produced_not_consumed)
    lines.append('')
    if report.produced_not_consumed_weak:
        lines.append(
            f'CDK sets it, no direct os.environ read found, but the name appears as a quoted string '
            f'somewhere in the backend — likely consumed through indirection this tool does not trace '
            f'(a *args fallback-chain helper, for example); verify by hand before calling these dead '
            f'({len(report.produced_not_consumed_weak)}):'
        )
        lines.extend(f'  - {name}' for name in report.produced_not_consumed_weak)
        lines.append('')
    lines.append(f'backend reads it, CDK never sets it on any Lambda ({len(report.consumed_not_produced)}):')
    lines.extend(f'  - {name}' for name in report.consumed_not_produced)
    return lines


def _render_consumers(report: Report) -> list[str]:
    lines = [f'backend modules that touch a TABLE env var ({len(report.consumers)}):']
    for c in report.consumers:
        lines.append(f'  - {c.module}: {", ".join(c.env_vars)}  (~{c.read_ops} read call(s), ~{c.write_ops} write call(s) by op-name grep)')
    return lines


def render(report: Report) -> str:
    lines = ['TABLE MAP — env var -> physical table, alias groups, producer/consumer gaps', '']
    lines += _render_physical_tables(report)
    lines.append('')
    lines += _render_alias_groups(report)
    lines.append('')
    lines += _render_inconsistent(report)
    lines.append('')
    lines += _render_producer_consumer_gaps(report)
    lines.append('')
    lines += _render_consumers(report)
    if report.unresolved:
        lines.append('')
        lines.append(f'unresolved (needs a human, not a guess) ({len(report.unresolved)}):')
        lines.extend(f'  - {u}' for u in report.unresolved)
    return '\n'.join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--no-write', action='store_true')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_report()

    if args.json:
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
    else:
        print(render(report))

    if not args.no_write:
        path = write_proof('table_map', asdict(report), read_deployed=False)
        if not args.json:
            print(f'\nproof: {path}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
