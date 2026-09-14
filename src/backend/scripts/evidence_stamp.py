"""Self-locating stamp for every proof this project writes.

A *proof* is a JSON file recording what was observed, when, and — this is the
part that was missing — **about exactly which code**. Without the last part a
proof cannot be reproduced, compared, or bisected against; it records that
something was once true without saying where to stand to see it again.

Every tool in this directory that observes the live system writes its result
through :func:`write_proof`, so every proof carries the same stamp:

    git_sha        the exact commit the observer was standing on
    git_dirty      True if uncommitted changes were present — see below
    git_branch     for human orientation only; SHAs are the real address
    deployed_sha   the commit the *stack* says it is running (see DeployedGitSha
                   in service_stack.py). None when it cannot be read.
    stack          which stack answered — dev and devx give different answers
    timestamp      UTC, ISO-8601

``git_dirty`` is load-bearing. A proof taken from a dirty tree describes code
that exists nowhere but one laptop and will be overwritten by the next edit:
you cannot check it out, cannot bisect from it, and cannot tell whether the
result came from the commit or from the uncommitted edit. Such proofs are still
written — the data is real — but they are marked, and gates must refuse them.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

DEFAULT_STACK: Final[str] = 'CareerVpCrudDevx'
SHA_OUTPUT_KEY: Final[str] = 'DeployedGitSha'


def _repo_root() -> Path:
    """The repository root, so proofs land in one place regardless of cwd.

    Every tool here is run from a different directory — make from src/backend,
    playwright from src/frontend, a human from anywhere — and a relative
    evidence path silently scatters proofs into three directories that never
    get compared. Anchoring on the git root is what keeps them comparable.
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return Path.cwd()


REPO_ROOT: Final[Path] = _repo_root()
DEFAULT_EVIDENCE_DIR: Final[Path] = REPO_ROOT / 'docs' / 'evidence'


def _git(*args: str) -> str | None:
    """Run a git command, returning stripped stdout or None if it fails."""
    try:
        result = subprocess.run(
            ['git', *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
    return result.stdout.strip()


def git_sha() -> str | None:
    """The full SHA of HEAD — the address of the code being observed."""
    return _git('rev-parse', 'HEAD')


def git_branch() -> str | None:
    return _git('rev-parse', '--abbrev-ref', 'HEAD')


def git_dirty() -> bool:
    """True when the working tree has changes git has not recorded.

    Anything non-empty from ``git status --porcelain`` counts, including
    untracked files: an untracked module can change behaviour just as much as
    a modified one.
    """
    status = _git('status', '--porcelain')
    return bool(status)


def dirty_paths() -> list[str]:
    """The files making the tree dirty, so a failing gate can say which."""
    status = _git('status', '--porcelain')
    if not status:
        return []
    return [line[3:] for line in status.splitlines() if len(line) > 3]


def deployed_sha(stack: str = DEFAULT_STACK) -> tuple[str | None, str]:
    """Read the commit the stack says it is running.

    Returns ``(sha, detail)``. ``sha`` is None when the answer cannot be
    obtained — no credentials, no such stack, or a stack deployed before the
    DeployedGitSha output existed. The detail says which, because "I could not
    check" and "it is wrong" require different responses.
    """
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:  # pragma: no cover - boto3 is a declared dependency
        return None, 'boto3 not importable'

    try:
        client = boto3.client('cloudformation')
        response = client.describe_stacks(StackName=stack)
    except (BotoCoreError, ClientError) as exc:
        return None, f'cannot describe {stack}: {type(exc).__name__}'

    stacks = response.get('Stacks', [])
    if not stacks:
        return None, f'{stack} not found'

    for output in stacks[0].get('Outputs', []):
        if output.get('OutputKey') == SHA_OUTPUT_KEY:
            value = str(output.get('OutputValue', ''))
            return value, 'read from stack output'

    return None, f'{stack} has no {SHA_OUTPUT_KEY} output (deployed before stamping existed?)'


def stamp(stack: str = DEFAULT_STACK, *, read_deployed: bool = True) -> dict[str, Any]:
    """Build the self-locating header shared by every proof."""
    sha = git_sha()
    deployed, deployed_detail = (None, 'not requested')
    if read_deployed:
        deployed, deployed_detail = deployed_sha(stack)

    return {
        'git_sha': sha,
        'git_short': sha[:7] if sha else None,
        'git_branch': git_branch(),
        'git_dirty': git_dirty(),
        'dirty_paths': dirty_paths(),
        'deployed_sha': deployed,
        'deployed_sha_detail': deployed_detail,
        # True only when we positively confirmed the stack runs this commit.
        # Unknown is not the same as matching, so None is a real answer here.
        'deployed_matches_head': (deployed == sha) if (deployed and sha) else None,
        'stack': stack,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }


def write_proof(
    kind: str,
    payload: dict[str, Any],
    *,
    stack: str = DEFAULT_STACK,
    out_dir: Path = DEFAULT_EVIDENCE_DIR,
    read_deployed: bool = True,
) -> Path:
    """Write one proof and return its path.

    Filenames embed the timestamp and short SHA so that two proofs of the same
    kind never collide and the pair worth comparing is obvious from ``ls``.
    """
    header = stamp(stack, read_deployed=read_deployed)
    document = {'kind': kind, **header, **payload}

    out_dir.mkdir(parents=True, exist_ok=True)
    slug = header['timestamp'].replace(':', '').replace('-', '').split('.')[0]
    short = header['git_short'] or 'nogit'
    path = out_dir / f'{kind}-{slug}-{short}.json'
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return path


def latest_proof(kind: str, out_dir: Path = DEFAULT_EVIDENCE_DIR) -> Path | None:
    """The most recent proof of a kind, by filename (which sorts by time)."""
    candidates = sorted(out_dir.glob(f'{kind}-*.json'))
    return candidates[-1] if candidates else None


def describe_stamp(header: dict[str, Any]) -> str:
    """One human-readable line summarising a stamp, for CLI headers."""
    short = header.get('git_short') or 'unknown'
    dirty = ' DIRTY' if header.get('git_dirty') else ''
    match = header.get('deployed_matches_head')
    if match is True:
        deploy_note = 'stack runs this commit'
    elif match is False:
        deployed = header.get('deployed_sha') or '?'
        deploy_note = f'stack runs {deployed[:7]} — NOT this commit'
    else:
        deploy_note = f'deployed commit unknown ({header.get("deployed_sha_detail")})'
    return f'{header.get("stack")} · {short}{dirty} · {deploy_note}'
