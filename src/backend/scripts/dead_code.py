"""dead_code.py — orphaned modules: every .py file no other module imports.

Why this exists
----------------
"Grep for the name, see no hits" is not an inventory (see CLAUDE.md and every
handoff in this repo that repeats the warning). This tool builds an actual
import graph and reports what is unreachable from a stated, checkable set of
entry points — so the claim "nothing imports this" is a graph fact, not an
impression.

Two independent package roots, never one graph
------------------------------------------------
`src/backend/careervp/` and `infra/careervp/` are both Python packages named
`careervp`, but they run in different processes with different ``sys.path``
roots (the Lambda runtime vs. the local CDK synth) and never import from each
other despite sharing a package name. Building one merged graph would let an
`infra/careervp/x.py` accidentally "reach" `src/backend/careervp/x.py` just
because the dotted names collide — wrong, and silently so. This tool keeps two
separate graphs and never lets an edge cross between them.

The trap this exists to dodge
-------------------------------
CDK never *imports* a Lambda handler module — it names it by **string**
(``handler="careervp.handlers.x.lambda_handler"``). A naive import-graph walk
sees no edge into any of the ~27 handler modules and reports all of them dead.
Entry points are therefore seeded explicitly, before the graph is walked:
    - every handler string in infra/careervp/*.py (regex, not import-based)
    - infra/app.py's own imports (the infra graph's sole human entry point)
    - every package's __init__.py (Python imports these implicitly whenever
      any submodule is imported — this tool simulates that)

Production vs. test-only
--------------------------
A module imported only by something under src/backend/tests/ is not the same
as a module imported by production code — deleting it breaks the test suite,
not nothing. This tool reports the two cases separately. Only a module with
*zero* incoming edges, from anywhere, is reported ORPHANED.

What this cannot tell you
----------------------------
Reachable-in-the-import-graph is necessary but not sufficient for "actually
deployed": a CDK method can define a Lambda's handler string yet never be
*called*, so the Lambda is never created and the handler never runs in
production even though this tool will not flag its module. (This repo has
exactly one such case: ``_add_vpr_lambda_integration`` in api_construct.py is
never invoked, so ``handlers/vpr_handler.py`` ships to no Lambda despite this
tool seeing its handler string and marking it reachable. Method-level
call-graph orphans are a different, harder check this tool does not attempt —
see docs/DEAD-CODE.md for that finding, found by manual trace.)

Usage
-----
    uv run python scripts/dead_code.py                 # human-readable report
    uv run python scripts/dead_code.py --json           # machine-readable
    uv run python scripts/dead_code.py --no-write        # skip the proof file

Exit code is always 0 — this is an inventory tool, not a gate. Nothing here
should auto-fail a build; a human reads the report and decides.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_stamp import REPO_ROOT, write_proof  # noqa: E402

EXCLUDE_PARTS: Final[frozenset[str]] = frozenset({'.build', 'cdk.out', '__pycache__', '.venv', 'node_modules', '.mypy_cache', '.pytest_cache'})

BACKEND_ROOT: Final[Path] = REPO_ROOT / 'src' / 'backend' / 'careervp'
BACKEND_TESTS_ROOT: Final[Path] = REPO_ROOT / 'src' / 'backend' / 'tests'
INFRA_ROOT: Final[Path] = REPO_ROOT / 'infra' / 'careervp'
INFRA_APP: Final[Path] = REPO_ROOT / 'infra' / 'app.py'

HANDLER_STRING_RE: Final[re.Pattern[str]] = re.compile(r'handler\s*=\s*"careervp\.handlers\.([a-zA-Z0-9_.]+)\.[a-zA-Z0-9_]+"')


def _iter_py(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in sorted(root.rglob('*.py')) if not any(part in EXCLUDE_PARTS for part in p.parts)]


def _module_name(path: Path, root: Path, package: str) -> tuple[str, bool]:
    """Return (dotted module name, is_package) for a file under `root`."""
    rel = path.relative_to(root).with_suffix('')
    parts = [package, *rel.parts]
    is_package = parts[-1] == '__init__'
    if is_package:
        parts = parts[:-1]
    return '.'.join(parts), is_package


def _ancestors(name: str) -> list[str]:
    """['a.b.c'] -> ['a', 'a.b', 'a.b.c'] — importing a name implicitly imports every ancestor package first."""
    parts = name.split('.')
    return ['.'.join(parts[: i + 1]) for i in range(len(parts))]


@dataclass
class ModuleGraph:
    package: str
    modules: dict[str, Path] = field(default_factory=dict)
    is_package: dict[str, bool] = field(default_factory=dict)
    edges: dict[str, set[str]] = field(default_factory=dict)  # importer -> {imported}, both known modules

    def add_module(self, name: str, path: Path, is_pkg: bool) -> None:
        self.modules[name] = path
        self.is_package[name] = is_pkg
        self.edges.setdefault(name, set())

    def containing_package(self, module: str) -> str:
        if self.is_package.get(module):
            return module
        return module.rsplit('.', 1)[0] if '.' in module else ''

    def resolve_relative(self, module: str, level: int, submodule: str | None) -> str | None:
        base = self.containing_package(module)
        parts = base.split('.') if base else []
        extra_up = level - 1
        if extra_up:
            if extra_up > len(parts):
                return None
            parts = parts[: len(parts) - extra_up]
        base = '.'.join(parts)
        if submodule:
            return f'{base}.{submodule}' if base else submodule
        return base or None

    def _import_targets(self, node: ast.Import) -> set[str]:
        return {alias.name for alias in node.names if alias.name == self.package or alias.name.startswith(f'{self.package}.')}

    def _import_from_targets(self, module: str, node: ast.ImportFrom) -> set[str]:
        if node.level > 0:
            resolved = self.resolve_relative(module, node.level, node.module)
            if resolved is None:
                return set()
            return {resolved, *(f'{resolved}.{alias.name}' for alias in node.names)}
        if node.module and (node.module == self.package or node.module.startswith(f'{self.package}.')):
            return {node.module, *(f'{node.module}.{alias.name}' for alias in node.names)}
        return set()

    def parse_edges(self, module: str) -> set[str]:
        """Targets this module's import statements resolve to, restricted to modules we know about."""
        path = self.modules[module]
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            return set()

        targets: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets |= self._import_targets(node)
            elif isinstance(node, ast.ImportFrom):
                targets |= self._import_from_targets(module, node)

        # Only keep edges into modules we actually found on disk in this graph,
        # plus their ancestor packages (Python imports parents implicitly).
        known: set[str] = set()
        for target in targets:
            if target in self.modules:
                known.update(_ancestors(target))
        return known

    def build(self) -> None:
        for module in list(self.modules):
            self.edges[module] = self.parse_edges(module)

    def bfs(self, seeds: set[str]) -> set[str]:
        seen: set[str] = set()
        queue: deque[str] = deque()
        for s in seeds:
            for ancestor in _ancestors(s):
                if ancestor in self.modules and ancestor not in seen:
                    seen.add(ancestor)
                    queue.append(ancestor)
        while queue:
            current = queue.popleft()
            for nxt in self.edges.get(current, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen


def _external_seeds(graph: ModuleGraph, files: list[Path]) -> set[str]:
    """Absolute-import targets found in files OUTSIDE the graph (tests/, app.py)."""
    seeds: set[str] = set()
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == graph.package or alias.name.startswith(f'{graph.package}.'):
                        seeds.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                if node.module == graph.package or node.module.startswith(f'{graph.package}.'):
                    seeds.add(node.module)
                    for alias in node.names:
                        seeds.add(f'{node.module}.{alias.name}')
    return {s for s in seeds if s in graph.modules}


def _handler_seeds(graph: ModuleGraph) -> set[str]:
    seeds: set[str] = set()
    for path in _iter_py(INFRA_ROOT):
        text = path.read_text(encoding='utf-8', errors='ignore')
        for match in HANDLER_STRING_RE.finditer(text):
            candidate = f'careervp.handlers.{match.group(1)}'
            if candidate in graph.modules:
                seeds.add(candidate)
    return seeds


@dataclass
class GraphReport:
    total_modules: int
    production_reachable: int
    test_only: list[str]
    orphaned: list[str]
    seeds: dict[str, list[str]]
    paths: dict[str, str]  # dotted module name -> path relative to repo root


def _paths_of(graph: ModuleGraph) -> dict[str, str]:
    return {name: path.relative_to(REPO_ROOT).as_posix() for name, path in graph.modules.items()}


def analyze_backend() -> GraphReport:
    graph = ModuleGraph(package='careervp')
    for path in _iter_py(BACKEND_ROOT):
        name, is_pkg = _module_name(path, BACKEND_ROOT, 'careervp')
        graph.add_module(name, path, is_pkg)
    graph.build()

    handler_seeds = _handler_seeds(graph)
    test_files = _iter_py(BACKEND_TESTS_ROOT)
    test_seeds = _external_seeds(graph, test_files)

    production_reachable = graph.bfs(handler_seeds)
    all_reachable = graph.bfs(handler_seeds | test_seeds)
    test_only = sorted(all_reachable - production_reachable)
    orphaned = sorted(set(graph.modules) - all_reachable)

    return GraphReport(
        total_modules=len(graph.modules),
        production_reachable=len(production_reachable),
        test_only=test_only,
        orphaned=orphaned,
        seeds={'handler_strings': sorted(handler_seeds)},
        paths=_paths_of(graph),
    )


def analyze_infra() -> GraphReport:
    graph = ModuleGraph(package='careervp')
    for path in _iter_py(INFRA_ROOT):
        name, is_pkg = _module_name(path, INFRA_ROOT, 'careervp')
        graph.add_module(name, path, is_pkg)
    graph.build()

    app_seeds = _external_seeds(graph, [INFRA_APP]) if INFRA_APP.exists() else set()
    reachable = graph.bfs(app_seeds)
    orphaned = sorted(set(graph.modules) - reachable)

    return GraphReport(
        total_modules=len(graph.modules),
        production_reachable=len(reachable),
        test_only=[],
        orphaned=orphaned,
        seeds={'app_py_imports': sorted(app_seeds)},
        paths=_paths_of(graph),
    )


def render(backend: GraphReport, infra: GraphReport) -> str:
    lines = ['DEAD CODE — orphaned modules (import-graph reachability, not a runtime trace)', '']
    for label, report in (('backend (src/backend/careervp)', backend), ('infra (infra/careervp)', infra)):
        lines.append(f'== {label} ==')
        lines.append(
            f'{report.total_modules} modules · {report.production_reachable} reachable from entry points'
            f' · {len(report.test_only)} test-only · {len(report.orphaned)} orphaned'
        )
        if report.test_only:
            lines.append('  test-only (no production entry point reaches these):')
            for m in report.test_only:
                lines.append(f'    - {m}  ({report.paths[m]})')
        if report.orphaned:
            lines.append('  orphaned (nothing imports these, anywhere):')
            for m in report.orphaned:
                lines.append(f'    - {m}  ({report.paths[m]})')
        else:
            lines.append('  orphaned: none')
        lines.append('')
    lines.append('Note: a module can be reachable here and still ship to no deployed Lambda if the')
    lines.append('CDK method that names its handler string is itself never called — see docs/DEAD-CODE.md.')
    return '\n'.join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--json', action='store_true', help='emit JSON instead of the report')
    parser.add_argument('--no-write', action='store_true', help='do not write a proof file')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    backend = analyze_backend()
    infra = analyze_infra()

    if args.json:
        print(json.dumps({'backend': asdict(backend), 'infra': asdict(infra)}, indent=2, sort_keys=True))
    else:
        print(render(backend, infra))

    if not args.no_write:
        path = write_proof(
            'dead_code',
            {'backend': asdict(backend), 'infra': asdict(infra)},
            read_deployed=False,
        )
        if not args.json:
            print(f'\nproof: {path}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
