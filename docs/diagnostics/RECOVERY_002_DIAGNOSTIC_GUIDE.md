# RECOVERY_002 Diagnostic Guide: Gap Questions DynamoDB Failures

## Status
- ✅ Code changes deployed (commit 3d365e4)
- ✅ Enhanced error diagnostics added
- ⏳ Awaiting live test results with detailed error messages

## Expected Error Response Format (After Deployment)
When gap questions POST fails, the error response will now include detailed diagnostics:

```json
{
  "error": "Failed to save gap questions. Details: table_name=... operation=save_gap_questions error_code=... message=...",
  "code": "DYNAMODB_ERROR"
}
```

## Diagnostic Decision Tree

### If error_code = ValidationException
**Probable Cause**: Schema/key validation error
- Check if `pk` and `sk` fields match table schema
- Verify no restricted field names in `questions` array
- Validate TTL field is Unix timestamp (integer)

### If error_code = ResourceNotFoundException
**Probable Cause**: Table doesn't exist or wrong name
- Verify table name from environment: `echo $GAP_QUESTIONS_TABLE_NAME`
- Confirm table exists in AWS DynamoDB console
- Check CDK output for actual table name created

### If error_code = AccessDeniedException
**Probable Cause**: Lambda permissions insufficient
- Check IAM role has `dynamodb:PutItem` permission on users table
- Verify role ARN in lambda execution role

### If error_code = ProvisionedThroughputExceededException
**Probable Cause**: Throughput exceeded (on-demand table shouldn't see this)
- If on-demand billing, check for throttled keys in CloudWatch metrics
- Consider increasing on-demand capacity

### If error_code = ItemCollectionSizeLimitExceededException
**Probable Cause**: Item too large
- Verify `questions` array isn't exceeding 400KB item size
- Check for unusually large AI-generated content

## Next Steps
1. Deploy commit 3d365e4 to AWS
2. Run live tests: `python3 -m pytest docs/refactor/live_tests/test_05_gap_analysis.py -v`
3. Capture detailed error message from response
4. Cross-reference with decision tree above
5. Apply specific fix based on error code

## Key Files for Debugging
- Lambda handler: `src/backend/careervp/handlers/gap_handler.py` (line 223-236)
- DAL operation: `src/backend/careervp/dal/dynamo_dal_handler.py` (line 526-557)
- Table config: `infra/careervp/api_db_construct.py` (line 85-89)
- Lambda env: `infra/careervp/api_construct.py` (line 1807-1816)

## Post-Fix Verification
Once error is identified and fixed:
1. Confirm live test passes: `test_generate_gap_questions` returns 200
2. Confirm read-after-write: `test_get_gap_questions` returns persisted questions
3. Verify regression metrics: `check_regression_delta.py --baseline live-test-results27.log --current live-test-resultsXX.log`
4. Get Architect approval before merging
