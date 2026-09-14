# The harness

Five commands. They answer "where am I", "did I move", and "is this deploy safe".
Nothing here describes the project — everything here measures it.

```
make preflight    are the facts I am about to rely on true?
make journey      how far does a customer get?   (N of 9)
make state        show both on one page
make compare      what changed between the last two proofs?
make review       classify a change set before touching dev/staging/prod
```

Run all of them from `src/backend/`.

## The loop

```
preflight   →  are my facts true?
journey     →  how far does a customer get?   (N of 9)
one change  →  aimed at step N+1
journey     →  did N go up?
                 up   → commit
                 down → REVERT FIRST, investigate second
                 flat → the change didn't do what you predicted; read the failing step
```

You are done when N = 9 on a stack that can be rebuilt from scratch.

## Proofs

Every tool writes a JSON *proof* to `docs/evidence/`. A proof records what was
observed, when, and **which exact code** — `git_sha`, `git_dirty`, and
`deployed_sha` (what the stack says it is running, via the `DeployedGitSha`
stack output).

Without those fields a result cannot be reproduced, compared, or bisected
against. With them:

```
make compare KIND=journey        # subtract the last two proofs
```

...tells you whether a regression is CODE, DEPLOYMENT, CONFIGURATION, or
EXTERNAL — which decides what investigation is worth starting.

**`git_dirty: true` marks a proof as non-reproducible.** It describes code that
exists on one laptop and is not in git; you cannot check it out and cannot
bisect from it. Run anything you like while dirty — the restriction is on
*recording a claim*, not on working. `git commit -am wip` costs five seconds.

## Three results, never two

`preflight` reports PASS, FAIL, or **UNKNOWN**. UNKNOWN means the fact could not
be checked. It is not PASS. Reading "I could not check whether access logging is
on" as "access logging is on" is the specific mistake that cost this project
months, and the third state exists to make that impossible.

## The change-set review

For dev, staging, or prod — anywhere with data:

```
make create-changeset            # creates, does not execute
make review STACK=CareerVpCrudDev
```

Every change is ruled GO, READ, or STOP. The only AWS knowledge required is
which resource types hold data; that list is four entries long and lives at the
top of `scripts/review_change.py`.

**STOP means applying this destroys data.** Usually `Replacement: True` on a
DynamoDB table, S3 bucket, or Cognito user pool: CloudFormation deletes and
recreates it, and the application is then pointed at an empty one.

## The journey

`src/frontend/tests/e2e/journey.spec.ts` — nine steps in the order a paying
customer performs them. It is the definition of done, and the only artifact in
this repo that can *disprove* a claim of progress.

Two rules for editing it:

1. **Never add a `TODO`.** A step either asserts something real or it does not
   exist. The 25 older specs in that directory contain 282 test blocks and 113
   live assertions — the rest are commented out, so they pass while proving
   nothing. Do not add to that pile.
2. **Never soften a step to make it pass.** Lowering the bar moves the number
   without moving the product, which is the only way this instrument can lie.

## Rules for the AI, and for you

Paste this at the top of any investigation session:

```
1. If a command exists that answers the question, run it. Do not tell me what
   you think first.
2. Label every claim: OBSERVATION (command + output), INFERENCE, or OPINION.
3. If I assert a fact, verify it before relying on it. Report if it is wrong.
4. If my prompt names a suspect or a likely cause, flag it as contamination
   before you start.
5. Never recommend on a judgment call. Cost the options; I decide.
```

And before acting on any claim about AWS: *if this is false, what have I just
done that I cannot undo?* If the answer is not "nothing", get the command first.
