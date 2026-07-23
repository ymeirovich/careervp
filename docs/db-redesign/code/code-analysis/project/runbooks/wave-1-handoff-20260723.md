# Wave 1 — Handoff, 2026-07-23

**Read this after `wave-1-status.md`, not instead of it.** Specifically read the 1.6 row and the
two new sections right after it — "1.6 live verification (2026-07-23)" and
"1.6 handoff (2026-07-23)" — this file is a short pointer into that detail, not a duplicate of it.
Every step below still opens with its own STANDING CHECK per `RUNBOOK-RULES.md`.

---

## 0. FIRST: confirm this session's commits actually made it to origin

**Do this before anything else — if it's not pushed, nothing below is real for anyone but this
machine.**

```
git fetch origin db-redesign
git log --oneline origin/db-redesign..db-redesign
```

Expect this to print nothing. If it prints commits, they didn't push — run `git push origin
db-redesign` and re-check. Do the same sanity check for `fix/p06-scratch-ssm-arns` if you touch it.

---

## 1. What's done — 1.6 (P-07 devx frontend cutover) is code-complete and deployed

All of it is described in detail in `wave-1-status.md`'s 1.6 row and the "live verification"
section under it. The one-paragraph version: the hardcoded dev-pool fallbacks are gone, the devx
Amplify origin is registered with both Cognito (callback/logout URLs) and the API's CORS
allow-list, both changes are deployed to `CareerVpCrudDevx` and live-verified via direct `aws`
reads (not trusted from a diff), and **a real login as `ymeirovich@gmail.com` against devx
succeeded completely end-to-end** — proven via two HAR captures plus a disposable-user replay of
the full OAuth code exchange, with the returned `id_token`'s `iss` claim confirmed against the
devx pool (`us-east-1_bAZ6jb6HP`), not the dev pool.

Three real bugs were found and fixed along the way, each with its own live-verified before/after —
read "1.6 live verification (2026-07-23)" in the ledger for the full story on each:

1. Cognito's adaptive security dead-ended the pool's first-ever login (no MFA to step up to) —
   fixed via a live `set-risk-configuration` call, not a code change.
2. `process.env[name]` (dynamic access) silently defeated Next.js's build-time env inlining, so
   every production build failed to authenticate regardless of config — fixed in `d0c53e2`.
3. The API's CORS allow-list is a *second*, separate list from Cognito's callback URLs, and needed
   the devx origin added too — fixed in two parts (`f340fbd` then `65c8d4f`, because the first
   attempt only edited a Python default that `cdk.json`'s context was silently overriding).

## 2. What's NOT done — the only thing blocking 1.1

Two of the seven required evidence wires are still uncaptured: **a forced 401 with an
exactly-one-refresh check, and sign-out.** Nothing else is blocking — this is not a code problem,
not a deploy problem, just an uncaptured verification step.

**Why it stalled:** the `claude-in-chrome` MCP connection dropped mid-session. Confirming this is
still true is your first real move:

```
# In-session: try loading the tools
ToolSearch query="select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__read_network_requests"
```

- **If tools load and connect:** drive the test yourself. Navigate to
  `https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com`, have the human log in (you cannot type
  their password), then tamper the token and capture the network trace per §3 below.
- **If they're still unavailable:** this is a per-*session* disconnect, not a per-*extension* one —
  a prior attempt to just retry from inside the same stuck session failed identically. Tell the
  human plainly that a fresh session (not a retry) is what fixes this, and fall back to walking
  them through the manual steps in §3 yourself.

## 3. The exact test to run (manual DevTools, if no browser tool)

1. On the already-logged-in dashboard tab: DevTools → **Application** → **Local Storage** →
   `https://db-redesign.d3j2wnm8g5clnw.amplifyapp.com`.
2. Find the key ending `.idToken` (`CognitoIdentityServiceProvider.10c72h0q6cshe7dh3tup6ek9de.<sub>.idToken`).
   Edit its value: a JWT is `header.payload.signature` — change a handful of characters in the
   **signature segment only** (after the final `.`). Leave `exp` (in the payload) untouched.
3. **Network** tab, "Preserve log" on, then reload the dashboard.
4. Watch for the first API call (e.g. `/users/me`): expect **401**.
5. Watch what happens next: expect **exactly one** retry, then either it succeeds or the app signs
   out cleanly. More than one retry, or a hang with neither outcome, is the actual bug this check
   exists to catch — report it as a finding, not a test failure.
6. Sign out. Confirm the `/logout` URL targets the db-redesign origin and the session actually
   clears (reload bounces to `/login`).

**One nuance that will confuse you if you don't know it going in:** this app's Cognito SDK
auto-refreshes silently inside `getSession()` (see `lib/auth.ts`) whenever it locally judges a
token expired — *before* the request interceptor ever sends anything. A naturally-expired token
therefore never reaches the app as an observable 401; only a token the client still believes valid
but the *server* rejects (the tamper above, or a real revocation) produces one. Don't spend time
waiting for a natural expiry to produce a 401 — it won't, by design.

## 4. Once you have both wires

1. Write the real evidence file:
   `docs/evidence/pkce-devx-verification-<UTC-timestamp>.json`, following the shape already
   committed at `docs/evidence/pkce-devx-verification-TEMPLATE.json` (which is explicitly
   `status: not_executed` and must not be mistaken for real evidence — copy and fill it in, don't
   edit it in place).
2. Flip the 1.6 row in `wave-1-status.md` to fully closed.
3. State plainly: **1.1 is unblocked.**

## 5. Separate, don't conflate: `fix/p06-scratch-ssm-arns`

Unrelated to P-07/1.6. One commit (`c62fb03`), pushed this session but not merged or PR'd. Fixes a
pre-existing scratch-mode SSM ARN bug found while running the regression suite for the 1.6 work —
needs its own review, not bundled into whatever closes 1.6.
