# Independent derivation, before opening P1 verdicts

HEAD is cea07992539c09724a4f05be3761f24b8f4e4d5f; working tree is dirty.
Instruction files found: root AGENTS.md and CLAUDE.md; .clauderules is incorporated by AGENTS.md.
The handoff's read-only audit, evidence classification, order, controls and output contract govern.
Repository preservation, mock-only tests, and deployed-state check apply. Implementation-only
formatting/type/naming/deployment rules do not authorize rewriting the dirty tree during a source audit.
PROGRESS.md and plan.md are not updated: no associated implementation lands. Model-selection
prose cannot change or verify the runtime model. Pricing/model strategy are context, not audit evidence.
CLAUDE.md explicitly selects tests/unit; integration probe execution must be separate.

Step 0: STS confirms 788159322332, presgen_user, us-east-1. Submit Lambda LastModified
2026-08-08T08:21:30.000+0000, CodeSha256 FvIo0I3Kkl7C8DQCrU+Y51tS/UH3DPafiwcnFZescEU=,
RevisionId 7f435504-b9f8-4f42-8cac-b021ae03c2eb, DEPLOYED_GIT_SHA null.
The cited service_stack.py addition is uncommitted and is a CfnOutput, not a Lambda variable.
Deployed-state verifier passed for devx; its scope is only one Lambda, two tables and a bucket prefix.

1. S0a: export _read_artifact passes identity to three branches but _read_vpr gets only job_id;
   unscoped results/{job_id}.json is converted to DOCX and presigned. Edge exploitability separate.
2. S0b: get_job(None) enters S3 response before owner guard. Missing row is sufficient;
   TTL timing and retention require separate evidence.
3. S11d: save_cv model_dump(json) feeds floats to DynamoDB; only ClientError and ValidationError
   are caught. GPA model can produce a float. save_vpr has same serialization shape, but no callers found.
4. S25: pending transition supplies empty partition key; conditional update cannot target real user row.
   update_gap_responses upserts state only if absent, not if cv_selected already exists.
5. S1: optional caller-supplied VPR fallback uses DAL get_vpr without user_id, then derives job context.
6. S2: SFN discriminator requires no httpMethod AND three top-level fields; ordinary HTTP-v2 JSON body
   does not place those fields at top level. Direct-invoke IAM authority is a separate boundary.
7. S6: parse error becomes [] then ten templates and successful Result; transport/API errors return failure.
8. S7: failed final gate returns successful Result with quality_warning; no consumers found outside generator.
   Minimal executive summary is canned, score 50, with an embedded validation concern.
9. S8: cover-letter artifact DAL queries gap keys userId/questionId; wrong schema returns empty context.
10. S10: _do_stop_chain swallows three classes of failure; cancel ignores Result from primary job update.
11. S11: cancel writes lack conditions. Cover letter uses canonical read/query/write; CV uses legacy keys.
    Claimed cross-schema phantom needs a reachable mixed-schema read, not just absence of a condition.
12. S23: requirement tokenized once per call, evidence tokenized each pair; accumulated achievements uncapped.
13. S26: company scraped text IS truncated; names and job/gap model text lack max_length.
    Company router has separate system prompt; gap/interview concatenate system/user before generate.
14. K9: cleanup requires DYNAMODB_TABLE_NAME before try. Missing variable must raise.
15. G1: auth_utils accepts only sub under REST/JWT authorizer shapes; fails closed otherwise.
16. G4: list wrappers call DAL; LastEvaluatedKey loops exist and need paging control.
17. PREMISE-P2: users alias, legacy/canonical key builders and different table resolver chains coexist;
    this cannot alone explain auth, floats, cancellation and prompt issues.
18. PREMISE-P3: AST any-Raise is only a syntactic classifier, not proof an exception surfaces.
19. PREMISE-P4: probe explicitly requires 401 from forged identity headers. Registry pins export
    moduleType=cv_tailored. Unit command cannot execute the integration probe merely by importing registry.
20. PREMISE-P5: KnowledgeRepository has a source caller in knowledge_base_handler; writes pk/sk.
    No infrastructure reference to that handler found. Zero table rows cannot prove zero historical use.
