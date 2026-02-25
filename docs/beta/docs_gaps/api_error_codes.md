# CareerVP API Error Codes Reference

**Version:** 1.0 (Beta)
**Last Updated:** 2026-02-25

---

## Overview

This document provides a reference for all API error codes returned by CareerVP endpoints.

---

## HTTP Status Codes

| Status Code | Name | Description |
|-------------|------|-------------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Request accepted, processing async |
| 400 | Bad Request | Invalid request format |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Access denied |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 502 | Bad Gateway | Upstream error |
| 503 | Service Unavailable | Service temporarily unavailable |
| 504 | Gateway Timeout | Upstream timeout |

---

## Error Response Format

All errors follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {} // Optional additional details
}
```

---

## Authentication Errors (401)

### AUTH_INVALID_CREDENTIALS

**HTTP:** 401
**Message:** "Invalid email or password"

**Cause:** Wrong email or password combination.

**Resolution:**
- Check your email address
- Verify your password is correct
- Try password reset if needed

---

### AUTH_TOKEN_EXPIRED

**HTTP:** 401
**Message:** "Token has expired"

**Cause:** Your access token has expired.

**Resolution:**
- Use your refresh token to get a new access token
- Call POST /auth/refresh

---

### AUTH_TOKEN_INVALID

**HTTP:** 401
**Message:** "Invalid token"

**Cause:** Token is malformed or tampered with.

**Resolution:**
- Log in again to get a fresh token

---

### AUTH_MISSING_TOKEN

**HTTP:** 401
**Message:** "Missing authorization header"

**Cause:** No authentication token provided.

**Resolution:**
- Include Authorization header: `Bearer <token>`

---

## Authorization Errors (403)

### FORBIDDEN_NOT_OWNER

**HTTP:** 403
**Message:** "You do not have permission to access this resource"

**Cause:** Trying to access another user's resource.

**Resolution:**
- Ensure you're accessing your own resources
- Check the resource ID

---

### FORBIDDEN_INSUFFICIENT_PERMISSIONS

**HTTP:** 403
**Message:** "Insufficient permissions"

**Cause:** Your account doesn't have required permissions.

**Resolution:**
- Contact support if you believe you should have access

---

### FORBIDDEN_TRIAL_EXPIRED

**HTTP:** 403
**Message:** "Trial period has expired"

**Cause:** Your 14-day trial has ended.

**Resolution:**
- Upgrade to a paid plan to continue using CareerVP

---

### FORBIDDEN_APPLICATION_LIMIT

**HTTP:** 403
**Message:** "Application limit reached"

**Cause:** You've used all 3 free applications.

**Resolution:**
- Upgrade to a paid plan for unlimited applications

---

## Validation Errors (400/422)

### VALIDATION_REQUIRED_FIELD

**HTTP:** 400
**Message:** "Required field is missing: {field}"

**Cause:** A required field was not provided.

**Resolution:**
- Provide the required field
- Check API documentation for required fields

---

### VALIDATION_INVALID_FORMAT

**HTTP:** 422
**Message:** "Invalid {field} format"

**Cause:** Field value doesn't match expected format.

**Resolution:**
- Check the expected format (e.g., email, URL)
- Example: email must be valid email format

---

### VALIDATION_TOO_SHORT

**HTTP:** 422
**Message:** "Field {field} must be at least {min} characters"

**Cause:** Field value is too short.

**Resolution:**
- Provide a value meeting minimum length

---

### VALIDATION_TOO_LONG

**HTTP:** 422
**Message:** "Field {field} must be at most {max} characters"

**Cause:** Field value is too long.

**Resolution:**
- Shorten the value to meet maximum length

---

## Resource Errors (404)

### NOT_FOUND

**HTTP:** 404
**Message:** "{resource} not found"

**Cause:** The requested resource doesn't exist.

**Resolution:**
- Check the resource ID
- Ensure the resource hasn't been deleted

---

### CV_NOT_FOUND

**HTTP:** 404
**Message:** "CV not found"

**Cause:** The CV ID doesn't exist or doesn't belong to you.

**Resolution:**
- Check the CV ID
- List your CVs to see available IDs

---

### JOB_NOT_FOUND

**HTTP:** 404
**Message:** "Job not found"

**Cause:** The job application doesn't exist or doesn't belong to you.

**Resolution:**
- Check the job ID
- List your jobs to see available IDs

---

### USER_NOT_FOUND

**HTTP:** 404
**Message:** "User not found"

**Cause:** User account doesn't exist.

**Resolution:**
- Check the user ID
- Register a new account if needed

---

## Rate Limiting (429)

### RATE_LIMIT_EXCEEDED

**HTTP:** 429
**Message:** "Too many requests. Please try again later."

**Cause:** You've made too many requests in a short period.

**Resolution:**
- Wait before making more requests
- Use exponential backoff for retries

---

## Async Processing Errors

### JOB_NOT_FOUND

**HTTP:** 404
**Message:** "Job not found"

**Cause:** The async job ID doesn't exist.

**Resolution:**
- Check the job ID
- The job may have been deleted

---

### JOB_STATUS_INVALID

**HTTP:** 400
**Message:** "Invalid job status transition"

**Cause:** Can't transition from current status.

**Resolution:**
- Wait for job to complete before performing actions

---

### JOB_FAILED

**HTTP:** 500
**Message:** "Job processing failed: {reason}"

**Cause:** The async job failed to process.

**Resolution:**
- Check the error details
- Try creating the job again
- Contact support if issue persists

---

## File Upload Errors

### UPLOAD_FILE_TOO_LARGE

**HTTP:** 400
**Message:** "File exceeds maximum size of {max}MB"

**Cause:** Uploaded file is too large.

**Resolution:**
- Reduce file size
- Use a file under 10MB

---

### UPLOAD_INVALID_FORMAT

**HTTP:** 400
**Message:** "Invalid file format. Supported: {formats}"

**Cause:** File type not supported.

**Resolution:**
- Use PDF, DOCX, or TXT format

---

### UPLOAD_FAILED

**HTTP:** 500
**Message:** "File upload failed"

**Cause:** Server error during upload.

**Resolution:**
- Try again
- Contact support if persists

---

## Trial & Billing Errors

### TRIAL_ALREADY_STARTED

**HTTP:** 400
**Message:** "Trial already started"

**Cause:** Trial was already activated.

**Resolution:**
- No action needed, trial is active

---

### TRIAL_EXPIRED

**HTTP:** 403
**Message:** "Trial period has expired"

**Cause:** 14-day trial period ended.

**Resolution:**
- Upgrade to continue using CareerVP

---

### APPLICATION_LIMIT_REACHED

**HTTP:** 403
**Message:** "Maximum applications reached"

**Cause:** All 3 free applications used.

**Resolution:**
- Upgrade to paid plan for unlimited

---

### SUBSCRIPTION_NOT_FOUND

**HTTP:** 404
**Message:** "No active subscription found"

**Cause:** No valid subscription on account.

**Resolution:**
- Purchase a subscription

---

## Generic Errors

### INTERNAL_SERVER_ERROR

**HTTP:** 500
**Message:** "Internal server error"

**Cause:** An unexpected error occurred.

**Resolution:**
- Try again
- Contact support with request details

---

### SERVICE_UNAVAILABLE

**HTTP:** 503
**Message:** "Service temporarily unavailable"

**Cause:** Service is down for maintenance or overloaded.

**Resolution:**
- Wait and try again
- Check status page if available

---

## Handling Errors

### Retry Strategy

For transient errors (500, 502, 503, 429), implement retry with exponential backoff:

```python
import time

def retry_with_backoff(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except RateLimitError:
            wait_time = 2 ** i
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

### Error Logging

Always log:
- Full error response
- Request that caused the error
- Timestamp
- User ID (if authenticated)

---

## Getting Help

If you encounter persistent errors:

1. Note the error code and message
2. Note the request that caused it
3. Contact support with details
