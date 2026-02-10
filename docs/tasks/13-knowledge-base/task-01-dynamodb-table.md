# Task 13-KB-01: DynamoDB Table CDK Definition

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical - Foundation)
**Estimated Effort:** 1 hour
**Parent:** 13-knowledge-base/PLAN.md

---

## Objective

Add the Knowledge Base DynamoDB table to the CDK infrastructure.

## Requirements

1. [ ] Add `knowledge_base_table` to `api_db_construct.py`
2. [ ] Use PAY_PER_REQUEST billing mode
3. [ ] Define partition key: `pk` (String)
4. [ ] Define sort key: `sk` (String)
5. [ ] Add TTL attribute: `ttl`
6. [ ] Add GSI for querying by knowledge type (optional)
7. [ ] Export table name and ARN for Lambda access
8. [ ] Grant read/write permissions to relevant Lambda functions

## Files Modified

- `infra/careervp/api_db_construct.py`

## Implementation Notes

```python
# Example structure
self.knowledge_base_table = dynamodb.Table(
    self, "KnowledgeBaseTable",
    table_name=f"{stack_name}-knowledge-base",
    partition_key=dynamodb.Attribute(
        name="pk",
        type=dynamodb.AttributeType.STRING
    ),
    sort_key=dynamodb.Attribute(
        name="sk",
        type=dynamodb.AttributeType.STRING
    ),
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
    removal_policy=RemovalPolicy.RETAIN,
    time_to_live_attribute="ttl"
)
```

## Validation Checklist

- [ ] Table defined in CDK
- [ ] `cdk synth` succeeds
- [ ] Table name follows naming convention
- [ ] TTL enabled
- [ ] Lambda permissions granted

## Tests

- `tests/jsa_skill_alignment/test_knowledge_base_alignment.py::test_knowledge_base_table_in_cdk`
