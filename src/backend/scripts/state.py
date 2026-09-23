"""STATE — one page showing where the project actually is, right now.

This is a *view*, not a record. It has no author, holds no prose, and is
regenerated from proofs every time it runs. If it ever contains a fact that is
not present in one of its inputs, it has failed and should be deleted.

Three properties keep it from decaying into another status document:

  * Nobody writes it, so it cannot contain a claim no command backs.
  * It is rebuilt rather than updated, so it cannot go stale.
  * It has a fixed shape — nine journey steps — so it cannot grow without bound.

Its output is gitignored on purpose. The proofs underneath it are committed;
the rendering is disposable.

Usage
-----
    uv run python scripts/state.py              # write state/index.html
    uv run python scripts/state.py --print      # terminal summary only
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_stamp import DEFAULT_EVIDENCE_DIR, REPO_ROOT, latest_proof  # noqa: E402

STATE_DIR: Final[Path] = REPO_ROOT / 'state'
STEP_IDS: Final[tuple[str, ...]] = ('J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 'J9')


def load(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return None


def classify_step(value: str) -> tuple[str, str]:
    """Map a step result to (symbol, css class). Three states, never two."""
    if value == 'pass':
        return '✔', 'pass'
    if value.startswith('fail'):
        return '✖', 'fail'
    return '○', 'unknown'


def render_terminal(journey: dict[str, Any] | None, preflight: dict[str, Any] | None) -> str:
    lines: list[str] = []

    if preflight:
        premises = preflight.get('premises', [])
        counts = {status: sum(1 for p in premises if p.get('status') == status) for status in ('PASS', 'FAIL', 'UNKNOWN')}
        lines.append(f'PREFLIGHT  {counts["PASS"]} pass · {counts["UNKNOWN"]} unknown · {counts["FAIL"]} fail    ({preflight.get("timestamp", "?")})')
        for premise in premises:
            if premise.get('status') != 'PASS':
                lines.append(f'  {premise.get("status"):8} {premise.get("name")}: {premise.get("detail")}')
    else:
        lines.append('PREFLIGHT  no proof found — run: make preflight')

    lines.append('')

    if not journey:
        lines.append('JOURNEY    no proof found — run: make journey')
        return '\n'.join(lines)

    reached = journey.get('journey_reached', 0)
    total = journey.get('journey_total', len(STEP_IDS))
    dirty = '  [DIRTY — not reproducible]' if journey.get('git_dirty') else ''
    lines.append(f'JOURNEY    REACHED {reached} of {total}   @ {journey.get("git_short", "?")}{dirty}')
    lines.append('')

    names = journey.get('step_names', {})
    steps = journey.get('steps', {})
    for step_id in STEP_IDS:
        value = str(steps.get(step_id, 'not run'))
        symbol, _ = classify_step(value)
        name = str(names.get(step_id, ''))
        marker = '   ← here' if value.startswith('fail') else ''
        detail = f'  {value}' if value not in {'pass', 'not reached', 'not run'} else ''
        lines.append(f'  {symbol} {step_id}  {name:<22}{detail}{marker}')

    return '\n'.join(lines)


def _cell(value: str) -> str:
    symbol, css = classify_step(value)
    title = html.escape(value)
    return f'<td class="{css}" title="{title}">{symbol}</td>'


def render_html(journey: dict[str, Any] | None, preflight: dict[str, Any] | None) -> str:
    reached = journey.get('journey_reached', 0) if journey else 0
    total = journey.get('journey_total', len(STEP_IDS)) if journey else len(STEP_IDS)
    sha = journey.get('git_short', '?') if journey else '?'
    dirty = bool(journey.get('git_dirty')) if journey else False
    stack = journey.get('stack', '?') if journey else '?'
    shots = journey.get('screenshots', '') if journey else ''

    premise_rows = ''
    if preflight:
        for premise in preflight.get('premises', []):
            status = str(premise.get('status', 'UNKNOWN'))
            css = {'PASS': 'pass', 'FAIL': 'fail'}.get(status, 'unknown')
            premise_rows += (
                f'<tr><td class="{css}">{status}</td>'
                f'<td>{html.escape(str(premise.get("name")))}</td>'
                f'<td class="detail">{html.escape(str(premise.get("detail")))}</td>'
                f'<td class="cmd">{html.escape(str(premise.get("command")))}</td></tr>'
            )
    else:
        premise_rows = '<tr><td class="unknown">?</td><td colspan="3">no preflight proof — run <code>make preflight</code></td></tr>'

    step_rows = ''
    if journey:
        names = journey.get('step_names', {})
        steps = journey.get('steps', {})
        for step_id in STEP_IDS:
            value = str(steps.get(step_id, 'not run'))
            shot = f'{shots}/{step_id}-{str(names.get(step_id, "")).replace(" ", "-")}.png' if shots else ''
            link = f'<a href="../{html.escape(shot)}">view</a>' if value in {'pass'} or value.startswith('fail') else ''
            step_rows += (
                f'<tr><td class="id">{step_id}</td>'
                f'<td>{html.escape(str(names.get(step_id, "")))}</td>'
                f'{_cell(value)}'
                f'<td class="detail">{html.escape(value if value != "pass" else "")}</td>'
                f'<td>{link}</td></tr>'
            )
    else:
        step_rows = '<tr><td colspan="5">no journey proof — run <code>make journey</code></td></tr>'

    dirty_banner = '<div class="banner">This position was measured from a DIRTY tree. It is not reproducible.</div>' if dirty else ''

    return f"""<!doctype html>
<meta charset="utf-8"><title>CareerVP — STATE</title>
<style>
 body {{ font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; margin: 2rem auto; max-width: 62rem; padding: 0 1rem; }}
 h1 {{ font-size: 1.1rem; margin: 0 0 .25rem; }}
 .sub {{ color: #666; margin-bottom: 1.5rem; }}
 .big {{ font-size: 2.4rem; font-weight: 700; letter-spacing: -.02em; }}
 table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; }}
 th, td {{ text-align: left; padding: .35rem .6rem; border-bottom: 1px solid #e5e5e5; vertical-align: top; }}
 th {{ font-weight: 600; color: #666; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }}
 .pass {{ color: #157f3d; }} .fail {{ color: #b3261e; font-weight: 700; }} .unknown {{ color: #8a6d00; }}
 .id {{ color: #666; }} .detail {{ color: #444; }} .cmd {{ color: #999; font-size: .78rem; }}
 .banner {{ background: #fff4e5; border-left: 3px solid #b26b00; padding: .6rem .8rem; margin-bottom: 1.5rem; }}
 footer {{ color: #999; font-size: .8rem; border-top: 1px solid #e5e5e5; padding-top: .8rem; }}
 @media (prefers-color-scheme: dark) {{
   body {{ background: #111; color: #ddd; }} th, td {{ border-color: #2a2a2a; }}
   .pass {{ color: #4ade80; }} .fail {{ color: #f87171; }} .unknown {{ color: #fbbf24; }}
   .detail {{ color: #bbb; }} .banner {{ background: #2a1f00; }}
 }}
</style>
<h1>CareerVP — STATE</h1>
<div class="sub">{html.escape(str(stack))} · {html.escape(str(sha))}{' · DIRTY' if dirty else ''}</div>
{dirty_banner}
<div class="big">REACHED {reached} of {total}</div>
<p class="sub">How far a customer gets today. This number is the project's position.</p>

<h2>Journey</h2>
<table><tr><th>step</th><th>name</th><th></th><th>detail</th><th>frame</th></tr>{step_rows}</table>

<h2>Preflight — premises this work rests on</h2>
<table><tr><th>status</th><th>premise</th><th>observed</th><th>command</th></tr>{premise_rows}</table>

<footer>
Generated by <code>scripts/state.py</code> from proofs in <code>docs/evidence/</code>.
No part of this page was written by hand. Regenerate with <code>make state</code>.
</footer>
"""


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Render the current position from the latest proofs')
    parser.add_argument('--dir', type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument('--out', type=Path, default=STATE_DIR / 'index.html')
    parser.add_argument('--print', dest='print_only', action='store_true')
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    journey = load(latest_proof('journey', args.dir))
    preflight = load(latest_proof('preflight', args.dir))

    print(render_terminal(journey, preflight))

    if not args.print_only:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_html(journey, preflight), encoding='utf-8')
        print(f'\npage: {args.out}')

    # A missing journey proof is not a failure — it means "go measure".
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
