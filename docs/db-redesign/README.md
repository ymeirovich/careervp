# CareerVP DB Redesign — Problem Dossier

This directory collects **root-cause writeups** of recurring data-architecture defects in
CareerVP, written to inform a ground-up redesign of the persistence layer. The audience is a
future Claude acting as an **AWS Serverless database architect** — assume deep AWS/DynamoDB
fluency but **no prior context** on this codebase.

Each document is a self-contained problem dossier: it states the symptom, reconstructs the
exact request/response chain, isolates the root cause(s), and ends with **design requirements**
the redesign must satisfy. Documents describe the system **as observed** (with live evidence and
`file:line` citations captured at the time of writing) — verify line numbers against current code
before acting, as they drift.

## Index

| # | Document | Problem in one line |
|---|----------|---------------------|
| 01 | [01-artifact-table-routing-and-vpr-id-model.md](01-artifact-table-routing-and-vpr-id-model.md) | Downstream artifacts (cover letter, interview prep) report "VPR missing" because the **reader, writer, and identifier model disagree**: artifacts are split across tables with incompatible key schemas, and the VPR is fetched by the wrong *id* (an artifact id) on the wrong *table*. |

## The throughline (read this first)

Every problem in this dossier is a symptom of **three unresolved architectural decisions**:

1. **No single home for an "artifact."** Generated artifacts live in *different* DynamoDB tables
   with *different, incompatible* key schemas (`pk/sk` vs `applicationId/artifactId` vs `job_id`).
   Which table a piece of code reads is decided by **environment-variable precedence**, not by a
   typed contract — so a reader and its writer routinely resolve to different physical tables.

2. **No canonical entity identifier.** The same logical thing is addressed by at least three
   distinct ids — `application_id` (== `job_id`), a per-artifact `*_artifact_id`, and a request
   field `vpr_id` — and different layers assume different ones. A row keyed by `application_id`
   is then looked up by an `artifact_id` that was never a key. The lookup cannot succeed regardless
   of which table is queried.

3. **Lazy / multi-table entity materialization.** An "application" exists as a `jobs-table` row
   before its `applications-table` row is created, so ownership and state live in different places
   at different times.

A redesign that fixes table routing **without** also fixing the identifier model will keep
producing this class of bug. See document 01 for the full proof.

## Related historical incidents (same class, pre-redesign patches)

These were patched in place; the redesign should make them structurally impossible:

- VPR-regenerate 409: Company Research write/read resolved different tables (`cr_job_id` vs
  `application_id` key, `pk/sk` vs `applicationId/artifactId` schema).
- AI-Assist 409 "upstream artifact missing": Lambda read CV/VPR from empty dedicated tables
  while the data lived in the single `users-table`; later corrected to per-artifact table envs.
- Ownership 403 on fresh applications: `applications-table` row not yet materialized; ownership
  had to fall back to the `jobs-table` record.
