# HANDOFF 09 — environment-coupled dead code, and the tests that would have caught it

**Model: Opus 5, high effort.** Fresh session at the repo root, on
`tools/proof-harness`.

Parent: `docs/handoff/2026-09-21-HANDOFF-08-j3-client-side-submit.md`. Handoff
08's Step 1 conclusion is **wrong** and is corrected below; its Step 0, Step 2
and its "carry forward" list still stand.

---

## The one-sentence version

A default keyed to the literal string `"dev"` silently disabled this product's
entire asynchronous artifact pipeline when P-26 renamed the environment to
`devx`, and the same pattern in six other places makes Lambdas read a
**different live environment's** DynamoDB tables.

---

## Step 0 — verify before trusting

| # | Command | Expected |
|---|---|---|
| 0.1 | `aws lambda get-function-configuration --region us-east-1 --function-name careervp-gap-api-lambda-devx --query 'Environment.Variables.ARTIFACT_CHAIN_ENABLED' --output text` | `false` ← **the bug** |
| 0.2 | `aws stepfunctions list-executions --region us-east-1 --state-machine-arn arn:aws:states:us-east-1:788159322332:stateMachine:careervp-artifact-chain-statemachine-devx --query 'length(executions)'` | `0` — never run, ever |
| 0.3 | `aws lambda get-function-configuration --region us-east-1 --function-name careervp-job-api-lambda-devx --query 'Environment.Variables.ENVIRONMENT' --output text` | `None` |
| 0.4 | `aws logs filter-log-events --region us-east-1 --log-group-name /aws/lambda/careervp-gap-api-lambda-devx --start-time 1790013400000 --filter-pattern ERROR --query 'events[0].message' --output text \| grep -o 'careervp-users-table-dev'` | `careervp-users-table-dev` ← devx Lambda, dev table |
| 0.5 | `grep -c 'FVS_ENABLED' src/backend/careervp/logic/*.py` | `0` — flag written, never read |
| 0.6 | `cd src/backend && uv run pytest -q --tb=no -p no:cacheprovider -p no:randomly \| tail -1` | `2058 passed, 48 skipped, 12 xfailed` |

---

## What is already established — do not re-derive

| Claim | Status |
|---|---|
| J3's 2-of-9 failure was client-side | **False.** `POST /jobs` → 403 `trial_expired`. Handoff 08 checked `application-api`; `/jobs` routes to `job-api` (`api_construct.py:3461`) |
| Trial record said `trial_active: true` | True but meaningless — `get_usage` computes it as stored flag **AND** `days_remaining > 0` (`trial_service.py:116`) |
| J4's first failure was a product bug | **False.** The Save button's spinner carries `aria-label="Saving"`, so its accessible name becomes `"Saving Save"` and `/^save$/` stops matching *at request start*. Fixed in `87f2e84` |
| J4 passes | **Only under toy input.** Under the real SysAid CV + posting it fails: gap generation is a synchronous LLM call in a Lambda whose timeout is **30s**; `platform.report` carries `"status":"timeout"` |

Current honest measurement: **3 of 9** under real input (`a73082b`), 4 of 9 under
toy input (`3497e4b`). The real-input number is the one that means anything.

---

## Step 1 — the inventory

### Class A — a missing variable resolves to *another live environment*

Shape: `explicit var → else build a name from ENVIRONMENT, default 'dev'`.

| Site | Guesses |
|---|---|
| `dal/subscription_repository.py:498` | users table — **firing in devx now** |
| `dal/jobs_repository.py:59` | vpr-jobs table |
| `handlers/vpr_submit_handler.py:64` | results bucket |
| `handlers/vpr_worker_handler.py:51` | results bucket |
| `handlers/vpr_status_handler.py:50` | results bucket |
| `logic/utils/constants.py:42` | `get_resource_name()` base |

Root enabler: **`ENVIRONMENT` is set on exactly one Lambda** —
`api_construct.py:2298` (auth-api). The other ~30 run with it unset.

`subscription_repository.py` is worse than the others: it reads `TABLE_NAME`,
which `job-api`, `gap-api` and `application-api` do not set (only `billing` and
`user-api` do). So `get_subscription` **always** fails in devx →
`QuotaService` swallows it → every subscriber is silently treated as a trial
user.

### Class B — capability gated on the environment's literal name

| Site | Dead in devx |
|---|---|
| `infra/careervp/api_construct.py:2705` | artifact chain — the whole async pipeline |
| `infra/careervp/api_construct.py:343` | `_build_api_custom_domain()` |
| `handlers/company_research_worker_handler.py:385` | `_send_chain_signal` — the Step Functions callback. Always falls to `_enqueue_vpr_standalone` |

Note the second consumer: enabling the flag changes behaviour in **two**
places, not one. Budget for that.

`_build_api_custom_domain` is doubly hardcoded — a pinned ACM cert ARN
(`api_construct.py:366`) and the literal domain `api.dev.careervp.com`. Even if
it ran under `devx` it would build *dev's* domain.

### Class C — dead code that is not environment-related

- `src/backend/careervp/infrastructure/stacks/cv_tailoring_stack.py` is a CDK
  stack in the **backend runtime tree**. Nothing imports it (every other grep
  hit is a `.build/` or `cdk.out/` copy). It is bundled into every Lambda
  deployment package.
- `FVS_ENABLED` is set only in that orphaned stack, is absent from the deployed
  `careervp-cvtailor-lambda-devx`, and **is read by nothing in the repo**. FVS
  is listed in `CLAUDE.md` as a core business rule.
- `handlers/auth_handler.py:249` hardcodes `region_name='us-east-1'` with no
  env fallback (the sibling at `auth_service.py:177` does it correctly).

### The counter-example — copy this pattern

`infra/careervp/frontend_stack.py::_resolve_enable_custom_domain` is how a flag
should look: explicit opt-in, documented resolution order (CDK context > env
var), defaults to *disabled*, and its docstring states the failure it prevents.
Nothing about it depends on an environment's name.

---

## Step 2 — the fix, in dependency order

**Do not reorder these.** Step 2.2 breaks every Lambda if shipped before 2.1.

### 2.1 — one line, fixes all six Class-A sites

`infra/careervp/api_construct.py:1199`, inside `_build_shared_table_env()`:

```python
"ENVIRONMENT": self.naming.environment,
```

26 Lambdas consume that helper. No backend change, no call-site change. Deploy
and verify with 0.3 before continuing.

### 2.2 — make a missing variable fail loudly instead of guessing

New `src/backend/careervp/logic/utils/env.py`:

```python
def resource_env() -> str:
    """The deploy environment. Never guesses — a wrong guess reads another
    environment's data, which is worse than not starting."""
    env = os.environ.get('ENVIRONMENT', '').strip()
    if not env:
        raise RuntimeError('ENVIRONMENT unset; refusing to guess a resource name')
    return env
```

Replace the six Class-A sites with `env = resource_env()`. Delete the `'dev'`
literals. Keep `auth_service.py:219`'s fail-closed `'prod'` default — it points
the safe way — but route it through the same helper.

### 2.3 — replace name-matching with a declared capability table

New `infra/careervp/environments.py`:

```python
@dataclass(frozen=True)
class EnvProfile:
    artifact_chain: bool
    api_custom_domain: bool

ENVIRONMENTS = {
    "dev":  EnvProfile(artifact_chain=True, api_custom_domain=True),
    "devx": EnvProfile(artifact_chain=True, api_custom_domain=False),
    "prod": EnvProfile(artifact_chain=True, api_custom_domain=True),
}

def profile(env: str) -> EnvProfile:
    if env not in ENVIRONMENTS:
        raise ValueError(f"No profile for {env!r}; add a row to environments.py")
    return ENVIRONMENTS[env]
```

Then `api_construct.py:343` → `if profile(self.naming.environment).api_custom_domain:`
and `:2705` → the `artifact_chain` equivalent.

**The property that matters:** a new environment name becomes a *synth-time
error*, not a silent `false`. P-26 would have failed the build.

### 2.4 — the 30s ceiling

Even with the chain on, the synchronous fallback stays broken: gap generation
is an LLM call inside a 30s request Lambda. Options, **costed, not picked**:

| | Change | Buys | Costs |
|---|---|---|---|
| A | Raise `gap-api` timeout to 300s | One line | API Gateway still 504s at 29s; only helps because the Lambda finishes writing |
| B | Make generation async (SQS/Step Functions) like every other module | Correct; matches the design | Real work; the chain already does this — 2.3 may make it moot |
| C | Stream/chunk the generation | Best UX | Largest change |

Prefer B *if* 2.3 lands, since the chain exists precisely for this. Confirm
before building A.

---

## Step 3 — tests that catch the next one

The existing guard, `infra/tests/infrastructure/test_cr_table_env_consistency.py:111`,
asserts `ARTIFACT_CHAIN_ENABLED == "true"` while synthesizing `dev`. It passes
and protects nothing. **A test pinned to one environment cannot catch an
environment-coupling bug.** Every test below is parameterized or static.

### 3.1 Infra synth, parameterized over every environment (highest value)

```python
@pytest.mark.parametrize("env", sorted(ENVIRONMENTS))
def test_no_foreign_environment_suffix_in_template(env):
    template = synth(environment=env)
    foreign = {e for e in ENVIRONMENTS if e != env}
    for literal in iter_string_literals(template):
        for other in foreign:
            assert not literal.endswith(f"-{other}"), (
                f"{env} template references {other} resource: {literal}"
            )
```

One test, one entire bug class. It fails on the `-dev` table today and would
have failed on `api.dev.careervp.com`. Beware the `dev`/`devx` prefix trap —
compare on the full suffix, never `startswith`.

```python
@pytest.mark.parametrize("env", sorted(ENVIRONMENTS))
def test_every_lambda_declares_its_environment(env):
    for fn in lambdas_in(synth(environment=env)):
        assert fn.env.get("ENVIRONMENT") == env, f"{fn.name} cannot name itself"
```

```python
@pytest.mark.parametrize("env", sorted(ENVIRONMENTS))
def test_capability_flags_match_declared_profile(env):
    want = profile(env)
    for fn in lambdas_consuming("ARTIFACT_CHAIN_ENABLED", synth(environment=env)):
        assert fn.env["ARTIFACT_CHAIN_ENABLED"] == str(want.artifact_chain).lower()
```

### 3.2 Flag producer/consumer contract

Catches **both** discovered failure modes in one test: a flag read but never
set (`ARTIFACT_CHAIN_ENABLED` in devx) and a flag set but never read
(`FVS_ENABLED`).

```python
def test_every_consumed_flag_is_produced_and_vice_versa():
    consumed = grep_env_reads("src/backend/careervp")      # os.environ.get('X_ENABLED')
    produced = grep_env_writes("infra/careervp")           # "X_ENABLED": ...
    assert consumed - produced == set(), f"read but never set: {consumed - produced}"
    assert produced - consumed <= KNOWN_UNUSED, f"set but never read: {produced - consumed}"
```

Keep `KNOWN_UNUSED` empty. If something must go on it, it needs a comment
naming the ticket that empties it again.

### 3.3 Static guard — the direct answer to "catch future hardcoded bugs"

```python
FORBIDDEN = [
    (r"""environment\s*==\s*['"](dev|devx|prod|staging)['"]""",
     "branch on a capability in environments.py, not an environment name"),
    (r"""environ\.get\(\s*['"]ENVIRONMENT['"]\s*,\s*['"]\w+['"]\s*\)""",
     "use resource_env(); never default to another environment"),
]

def test_no_environment_name_branching():
    for path in python_sources("src/backend/careervp", "infra/careervp"):
        for pattern, why in FORBIDDEN:
            assert not re.search(pattern, path.read_text()), f"{path}: {why}"
```

Add an `# allow-env-literal: <reason>` escape hatch honoured by the test, so a
legitimate exception is visible in review rather than invisible in a default.

### 3.4 Unit

- `resource_env()` raises when `ENVIRONMENT` is unset/blank.
- `SubscriptionRepository()` with no env vars raises rather than resolving a
  name. **Today it silently returns `careervp-users-table-dev` — write this
  test first and watch it fail.**
- `profile("newenv")` raises `ValueError`.

### 3.5 Integration (moto)

Stand up `careervp-users-table-devx` **and** `careervp-users-table-dev`, seed
them differently, run `QuotaService.check_access` with `ENVIRONMENT=devx`, and
assert the devx row was the one read. A test that only creates one table cannot
detect cross-environment reads — that is why this survived.

### 3.6 Regression / deployed smoke

Extend `preflight.py`: for every Lambda in the target stack, assert
`ENVIRONMENT` is present and equals the stack's environment, and that no env
var value ends with another environment's suffix. This is 3.1 applied to what
is actually deployed, which catches drift from a manual
`update-function-configuration`.

### 3.7 E2E

`journey.spec.ts` is already the regression, and it now records console errors,
failed requests and every 4xx/5xx **with its body** (`87f2e84`) — that capture
is what found the 504 and the 403. Do not remove it. Keep driving it with the
real SysAid input (`4f9e628`); the toy input hid the 30s ceiling for months.

---

## Step 4 — blast radius of what is already committed

Four commits on `tools/proof-harness`, unpushed:

```
a73082b  docs(evidence): journey 3 of 9 under real input — J4 exceeds a 30s Lambda
4f9e628  test(e2e): drive the journey with the real SysAid application
3497e4b  docs(evidence): journey 4 of 9 — J3 unblocked, J4 was a harness artifact
87f2e84  test(e2e): make the journey report what the browser already knows
```

They touch exactly one non-docs file: `src/frontend/tests/e2e/journey.spec.ts`.

```
push tools/proof-harness → 0 workflows. Changes no AWS infrastructure.
push db-redesign         → db-redesign-checks.yml :: deploy-backend-dev
                           stack CareerVpCrudDevx, action CREATE+EXECUTE
                           gate environment=devx (1 rule, 1 reviewer — real)
                           plus Amplify branch db-redesign auto-build (no gate)
```

**A test-only change triggers a full backend deploy**, because the path filter
matches `src/frontend/**` and does not read the diff. Recorded in `CLAUDE.md`
under "What actually fires". Never call a push inert because the change looks
like paperwork — that reasoning is what deleted ~70 resources on 2026-09-20.

---

## Environment state as left

- Trial record for the test user reset twice today; currently
  `created_at 2026-09-21T17:59:20Z`, `application_count 1`, active. **2 credits
  and 13 days remain — no reset needed.** Original pre-reset item is in the
  session scratchpad only; it was `created_at 2026-08-08`, already expired, so
  restoring it has no value.
- No stack, workflow, IAM or Lambda configuration was changed. The only devx
  mutation all session was that TRIAL row.
- `ARTIFACT_CHAIN_ENABLED` was **not** flipped. It is baked at synth time, so
  enabling it needs a deploy — operator's call, with blast-radius first.

## Ground rules

- `scripts/ops/blast-radius.sh <event> <branch>` before any merge, deploy,
  deletion or credential change; paste Action / Triggers / Undo before acting.
- Stop and ask on `CREATE+EXECUTE`, `NO ENVIRONMENT GATE`, or an environment
  with `0 rules`.
- Verify the environment; never infer it from a plan document.
- Run `CLAUDE.md`'s mandatory checks for every path you touch before committing.
  **Do not use `scripts/git/safe_commit.sh`** — four `docs/handoff/*.md` files
  are the operator's and stay dirty.
- One concern per commit.
- State your prediction before re-measuring, so the result cannot be
  rationalised afterwards. Two predictions were made this session; one was
  wrong, and saying so is the point of writing it down first.
