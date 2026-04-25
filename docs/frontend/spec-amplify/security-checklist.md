# Security & Compliance Checklist

Security review before deploying to production.

## Pre-Deployment Security Review

Complete these checks before going live:

---

## 1. Environment Variables & Secrets

### ✅ Required: No Secrets in Code

- [ ] No API keys in source code
- [ ] No AWS access keys in source code
- [ ] No database credentials in source code
- [ ] No Cognito secrets in source code
- [ ] `.env.local` is in `.gitignore`
- [ ] AWS credentials not in frontend code

**Verify:**
```bash
cd src/frontend
grep -r "AKIA\|sk_\|secret" app/ --exclude-dir=node_modules
# Should return nothing
```

### ✅ Required: Public Variables Only in NEXT_PUBLIC_*

**Allowed:**
```
NEXT_PUBLIC_API_URL = "https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod"
NEXT_PUBLIC_COGNITO_USER_POOL_ID = "us-east-1_WiHMRqLpe"
NEXT_PUBLIC_COGNITO_CLIENT_ID = "7blipbarsisbctqh6hlsj46sqa"
NEXT_PUBLIC_COGNITO_REGION = "us-east-1"
```

**Never put in NEXT_PUBLIC_*:**
- ❌ Cognito client secret (if using backend auth)
- ❌ Database connection strings
- ❌ Private API keys
- ❌ Auth tokens

**Verify:**
```bash
# Check next.config.js
grep -i "secret\|password\|key" src/frontend/next.config.js
# Should return nothing sensitive
```

### ✅ Required: Secrets in AWS Only

All build/deployment secrets stored in:
- AWS Secrets Manager (for CI/CD)
- GitHub Actions Secrets (for build steps)
- Environment variables in Amplify Console (encrypted)

---

## 2. CORS Security

### ✅ Required: Specific Origins (Not Wildcard)

**Good:**
```python
allow_origins=[
    "https://main.d123abc.amplifyapp.com",
    "https://app.careervp.com",
    "https://dev.careervp.com",
    "http://localhost:3000",  # dev only
]
```

**Bad:**
```python
allow_origins=["*"]  # ❌ Too permissive
allow_origins=["https://*.amplifyapp.com"]  # ❌ Wildcard
```

- [ ] Backend CORS uses specific origins (not `*`)
- [ ] Localhost not in production CORS
- [ ] No wildcard origins
- [ ] AllowCredentials = true (required for auth)

**Verify:** See `backend-cors.md` for verification steps

---

## 3. Cognito Authentication

### ✅ Required: Callback URLs Match Exactly

- [ ] Callback URLs on Amplify domains
- [ ] Callback URLs on custom domains (when ready)
- [ ] Callback URLs on localhost (dev only)
- [ ] No typos or variations in URLs
- [ ] All use HTTPS (except localhost)

**Verify:**
```
Config:  https://main.d123abc.amplifyapp.com/callback
Browser: https://main.d123abc.amplifyapp.com/callback  ← Exact match
```

**See:** `cognito-config.md` for full setup

### ✅ Required: Cognito Security Settings

In Cognito console, verify:

**User Pool Policies:**
- [ ] Require strong passwords (default: 8+ chars, mixed case, numbers)
- [ ] Password expiration configured (default: 90 days recommended)
- [ ] MFA optional or required (depends on compliance needs)

**User Pool Attributes:**
- [ ] Email verification required (for password resets)
- [ ] Email verified status checked at login

**Tokens:**
- [ ] ID token expiration < 1 hour (default: 60 min ✅)
- [ ] Access token expiration < 1 hour (default: 60 min ✅)
- [ ] Refresh token expiration reasonable (default: 30 days)

---

## 4. API Gateway Security

### ✅ Required: Authorization on All Protected Routes

- [ ] All sensitive endpoints require Authorization header
- [ ] API key or JWT validation enforced
- [ ] Public endpoints documented

**Verify:**
```bash
# Test protected endpoint without token
curl https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/applications

# Should return 401 Unauthorized
```

### ✅ Required: Rate Limiting

API Gateway has rate limits configured:
- [ ] Throttle limit: 10,000 req/sec (default)
- [ ] Burst limit: 5,000 req/sec (default)
- [ ] Consider per-user throttling for abuse prevention

### ✅ Required: Logging & Monitoring

- [ ] CloudWatch logs enabled for API Gateway
- [ ] CloudTrail enabled for all API calls
- [ ] Errors monitored and alerted
- [ ] Unusual traffic patterns trigger alerts

---

## 5. Frontend Security

### ✅ Required: HTTPS Only

- [ ] All traffic uses HTTPS (not HTTP)
- [ ] Amplify enforces HTTPS redirect
- [ ] Cognito uses HTTPS
- [ ] Backend API uses HTTPS

**Verify:** DevTools → Network tab, all requests start with `https://`

### ✅ Required: Content Security Policy (CSP)

CSP headers prevent XSS attacks.

**Check if Next.js has CSP configured:**
```javascript
// next.config.js should have:
headers: [
  {
    key: 'Content-Security-Policy',
    value: "default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self' https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com https://cognito-idp.us-east-1.amazonaws.com;"
  }
]
```

- [ ] CSP headers configured in Next.js
- [ ] CSP allows only needed domains
- [ ] Blocks inline scripts (except what Next.js needs)

**If not configured:** Add to `next.config.js`

### ✅ Required: No Sensitive Data in Logs

- [ ] Auth tokens not logged
- [ ] API keys not logged
- [ ] Passwords not logged
- [ ] User PII not logged unnecessarily

**Verify:**
```bash
# Check CloudWatch logs for sensitive data
aws logs filter-log-events \
  --log-group-name /aws/amplify/careervp-frontend \
  --filter-pattern "Authorization OR token OR password"

# Should return no results
```

### ✅ Required: XSS Protection

- [ ] All user input sanitized
- [ ] Frontend uses React (auto-escapes by default)
- [ ] No `dangerouslySetInnerHTML` with user input
- [ ] No eval() or similar dangerous functions

**Verify:**
```bash
grep -r "dangerouslySetInnerHTML\|eval(" src/frontend/app --exclude-dir=node_modules
# Should return nothing (or only safe usage)
```

### ✅ Required: CSRF Protection

- [ ] State parameters used in OAuth flow
- [ ] SameSite cookies set (default in modern browsers)
- [ ] POST endpoints validate CSRF tokens

**Verify:** Cognito OAuth flow includes `state` parameter (auto-handled by AWS)

---

## 6. Data Storage & Transmission

### ✅ Required: Auth Tokens Protected

**Storage:**
- [ ] Tokens stored in localStorage (acceptable for SPA)
- [ ] OR stored in HTTP-only cookies (better, requires backend)
- [ ] NOT stored in sessionStorage
- [ ] NOT stored in global variables

**Transmission:**
- [ ] Tokens sent only over HTTPS
- [ ] Authorization header used (not URL query param)
- [ ] Token never logged or exposed

**Verify:**
```javascript
// In browser console:
localStorage.getItem('authToken')
// Returns JWT (long string starting with eyJ)
// But NEVER expose in logs
```

### ✅ Required: Sensitive Data Not Cached

**HTTP Headers:**
- [ ] API responses have `Cache-Control: no-cache` for auth endpoints
- [ ] CloudFront respects cache headers
- [ ] User data never cached in browser

**Verify:**
```bash
# Check API response headers
curl -I https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/applications \
  -H "Authorization: Bearer <token>"

# Should show:
# Cache-Control: no-cache, no-store, must-revalidate
# or
# Cache-Control: private, no-cache
```

### ✅ Required: Database Security

Not directly relevant (frontend only), but verify backend:
- [ ] Database encryption at rest enabled
- [ ] Database backups encrypted
- [ ] Database access restricted to Lambda functions
- [ ] SQL injection prevention (use parameterized queries)

---

## 7. Dependency Security

### ✅ Required: No High-Risk Dependencies

Run dependency audit:

```bash
cd src/frontend
npm audit
```

- [ ] No critical vulnerabilities (CVSS > 9.0)
- [ ] No high vulnerabilities left unfixed
- [ ] Moderate issues have plans to fix

**Fix vulnerabilities:**
```bash
npm audit fix
npm update
```

### ✅ Required: Regular Updates

- [ ] Weekly dependency audit in CI/CD
- [ ] Automated PRs for updates (via Dependabot)
- [ ] Manual review before merging

---

## 8. Access Control & Permissions

### ✅ Required: IAM Policies Least Privilege

AWS IAM roles should only have necessary permissions:

**Amplify IAM Role:**
- [ ] Can read from GitHub repo (required)
- [ ] Can write to S3 bucket (required)
- [ ] Can invalidate CloudFront (required)
- [ ] Cannot delete resources
- [ ] Cannot modify other stacks

**Lambda Execution Role:**
- [ ] Can access DynamoDB (required)
- [ ] Can access S3 for uploads (required)
- [ ] Cannot access other resources
- [ ] Cannot modify IAM policies

**Verify:**
```bash
aws iam get-role --role-name AmplifyRole
# Check inline policies and attached policies
```

### ✅ Required: GitHub Security

- [ ] GitHub token has minimal scopes
- [ ] Branch protection enforced (require reviews)
- [ ] Only authorized users can merge
- [ ] Secrets not stored in GitHub repo

---

## 9. Monitoring & Alerting

### ✅ Required: Error Tracking

- [ ] Frontend errors logged (Sentry, CloudWatch, etc.)
- [ ] Backend errors logged to CloudWatch
- [ ] Alerts for critical errors

**Verify:**
```bash
aws logs describe-log-groups --region us-east-1 | grep careervp
# Should see log groups for:
# - API Gateway
# - Lambda functions
# - Amplify build logs
```

### ✅ Required: Performance Monitoring

- [ ] API latency monitored (CloudWatch)
- [ ] Frontend load time monitored
- [ ] Database query performance monitored
- [ ] Alerts for slow endpoints

---

## 10. Compliance & Legal

### ✅ Check: Privacy Policy

- [ ] Privacy policy exists and is accurate
- [ ] Policy linked from frontend
- [ ] Data collection described
- [ ] User consent mechanism (if required)

### ✅ Check: Terms of Service

- [ ] Terms exist and are clear
- [ ] User agrees before signup
- [ ] Liability limitations clear

### ✅ Check: Data Retention

- [ ] User data not retained longer than needed
- [ ] Logs purged after 30 days (or per policy)
- [ ] Deletion requests honored
- [ ] GDPR compliance (if EU users)

---

## Pre-Production Checklist

### Security Approval

Before deploying to production:

- [ ] All 10 sections reviewed
- [ ] No critical vulnerabilities
- [ ] All tests in `verification.md` pass
- [ ] Security team approved (if required)
- [ ] Deployment plan documented
- [ ] Rollback plan ready

### Go-Live Checklist

- [ ] Monitoring enabled
- [ ] On-call schedule active
- [ ] Incident response plan ready
- [ ] Customer communication plan ready
- [ ] Deployment window scheduled
- [ ] Team available for support

---

## Post-Deployment Security Review

After deployment:

### Week 1
- [ ] Monitor error rates (should be 0)
- [ ] Monitor API latency
- [ ] Check auth success rate
- [ ] Review CloudWatch logs for anomalies

### Week 2-4
- [ ] Run full dependency audit again
- [ ] Review access logs for suspicious activity
- [ ] Performance metrics stable
- [ ] User feedback positive

### Monthly
- [ ] Security audit (repeat this checklist)
- [ ] Dependency updates applied
- [ ] Logs purged per retention policy
- [ ] Backups tested

---

## Security Incident Response

If security issue found:

1. **Identify** — Understand scope and impact
2. **Contain** — Stop further exposure
3. **Remediate** — Fix the root cause
4. **Verify** — Confirm fix works
5. **Communicate** — Notify affected users (if needed)
6. **Learn** — Update processes to prevent recurrence

**Contact:** ymeirovich@gmail.com (if breach suspected)

---

**Status:** Ready to review
**Time required:** 30 minutes
**Approval:** Required before production deployment
