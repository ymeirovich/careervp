# Troubleshooting Guide

Common issues and solutions for Amplify deployment.

---

## Build Issues

### Build Fails: "npm run build" Error

**Symptom:** Amplify build fails with:
```
Error: npm ERR! code EWORKSPACE
or
Error: Cannot find module
```

**Solution:**

1. **Verify local build works:**
   ```bash
   cd src/frontend
   npm ci
   npm run build
   ```

2. **Check node_modules corruption:**
   ```bash
   rm -rf node_modules package-lock.json
   npm ci
   npm run build
   ```

3. **Check for TypeScript errors:**
   ```bash
   npm run typecheck
   ```

4. **Push fix to Git:**
   ```bash
   git add package.json
   git commit -m "fix: resolve build dependencies"
   git push
   ```

5. **Amplify rebuilds automatically**

---

### Build Fails: "outputFileTracing failed"

**Symptom:**
```
Error: Prerendering failed for some routes
Error: Failed to collect dependencies for /applications/[id]
```

**Solution:** This is expected — Next.js can't pre-render dynamic routes without `generateStaticParams()`.

**What to do:**
1. ✅ This is OK — dynamic routes render at runtime on client
2. ✅ Amplify handles it automatically
3. ✅ No action needed

If error blocks deploy, check `next.config.js` doesn't have `output: 'export'`.

---

### Build Slow (>10 minutes)

**Symptom:** Amplify build takes 10+ minutes

**Solution:**

1. **Clear build cache:**
   - Amplify Console → Settings
   - Click **"Clear build cache"**
   - Redeploy

2. **Check node_modules size:**
   ```bash
   cd src/frontend
   npm list
   # Look for duplicate dependencies
   ```

3. **Upgrade dependencies:**
   ```bash
   npm update
   npm ci
   npm run build
   ```

4. **Check for large files:**
   ```bash
   npm ls --depth=0 | grep npm-size
   ```

**Expected:** Build should complete in 3-5 minutes

---

## Deployment Issues

### Deployment Shows "In Progress" But Never Finishes

**Symptom:** Amplify shows "Building..." for >15 minutes

**Solution:**

1. **Check Amplify build logs:**
   - Amplify Console → Deployments
   - Click active deployment
   - Scroll to "Build log"
   - Look for stuck process

2. **Manually cancel:**
   - Amplify Console → Deployments
   - Click the running deployment
   - Look for **"Cancel deployment"** button

3. **Retry deployment:**
   - Amplify Console → Deployments
   - Click **"Redeploy"** on latest commit

---

### Deployment Succeeds But Site Shows 404

**Symptom:** 
```
Error: 404 Not Found
The request resource is not available
```

**Solution:**

1. **Verify correct URL:**
   - Check Amplify Console → Deployments
   - Copy the exact URL (not bookmarked URL)
   - URLs may change if branch changes

2. **CloudFront cache:**
   ```bash
   # Invalidate cache
   aws cloudfront create-invalidation \
     --distribution-id <DISTRIBUTION_ID> \
     --paths "/*" \
     --region us-east-1
   ```

3. **Check Amplify domain:**
   - Amplify Console → Domain management
   - Verify domain is "Active"
   - Wait 10+ minutes if recently added

---

## Page Load Issues

### Page Loads But Shows Blank Screen

**Symptom:** CloudFront URL loads, but nothing visible, no console errors

**Solution:**

1. **Check if page is loading:**
   - Open DevTools → Network tab
   - Reload page
   - Look for `_next/...` files loading
   - If no requests, JavaScript not running

2. **Check for errors in background:**
   - DevTools → Console tab
   - Look for error messages
   - See "Console Errors" section below

3. **Check for hydration mismatch:**
   - NextJS error: "Text content did not match"
   - Solution: Hard refresh (Ctrl+Shift+R)
   - If persists, bug in component rendering

4. **Verify environment variables loaded:**
   ```javascript
   // In console:
   process.env.NEXT_PUBLIC_API_URL
   // Should show API endpoint
   ```

---

### Page Takes >5 Seconds to Load

**Symptom:** Page blank for 5+ seconds before rendering

**Solution:**

1. **Check network speed:**
   - DevTools → Network tab
   - Right-click → Throttling → Select "Slow 3G"
   - Expected: Takes longer, but still loads

2. **Check CloudFront cache:**
   ```bash
   curl -I https://main.d123abc.amplifyapp.com \
     -H "X-Cache-Debug: true"
   
   # Look for header:
   # Via: CloudFront
   # Age: <seconds>
   
   # Age=0 means not cached (first visit)
   # Age>0 means cached (fast)
   ```

3. **Check bundle size:**
   ```bash
   # Run bundle analyzer
   npm run build:analyze
   # Look for large chunks
   ```

4. **Check API latency:**
   - DevTools → Network tab
   - Find API call
   - Look at "Time" column
   - If >1000ms, backend is slow

---

## Console Errors

### CORS Error: "Access to XMLHttpRequest Blocked"

**Symptom:**
```
CORS error: Access to XMLHttpRequest at 
'https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/applications'
from origin 'https://main.d123abc.amplifyapp.com' has been blocked
```

**Solution:**

1. **Verify backend CORS is deployed:**
   ```bash
   curl -X OPTIONS https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/applications \
     -H "Origin: https://main.d123abc.amplifyapp.com" \
     -H "Access-Control-Request-Method: GET" \
     -v
   
   # Should show:
   # Access-Control-Allow-Origin: https://main.d123abc.amplifyapp.com
   ```

2. **If header missing, redeploy backend:**
   ```bash
   cd infra
   cdk deploy CareerVpCrudDev --require-approval never
   ```

3. **Verify Amplify CloudFront URL is in CORS:**
   - See `backend-cors.md`
   - Add `https://main.d123abc.amplifyapp.com` to allow_origins
   - Redeploy

---

### Error: "redirect_uri mismatch"

**Symptom:**
```
Error: redirect_uri mismatch: 
The redirect_uri is not registered with the client
```

**Solution:**

1. **Verify Cognito callback URLs:**
   - AWS Cognito console
   - User Pool → App Clients
   - Check "Allowed callback URLs"
   - Should include: `https://main.d123abc.amplifyapp.com/callback`

2. **Check URL format exactly:**
   - Must match EXACTLY (including protocol, domain, path)
   - `https://` not `http://`
   - Full path `/callback` required

3. **Refresh Cognito console:**
   - F5 or Cmd+R
   - Verify changes saved

See `cognito-config.md` for full setup.

---

### Error: "Cannot read property 'xxx' of undefined"

**Symptom:**
```
TypeError: Cannot read property 'context' of undefined
```

**Solution:**

1. **Check if data is fetching:**
   - DevTools → Network tab
   - Look for pending API requests
   - Wait for response before accessing data

2. **Check data structure:**
   ```typescript
   // Safe access:
   const data = response?.applications?.[0]?.name
   // vs
   const data = response.applications[0].name  // ❌ Can fail if null
   ```

3. **Add error boundary:**
   - Check if ErrorBoundary component wraps the failing component
   - See `src/frontend/components/ErrorBoundary/`

---

## API Call Issues

### API Call Returns 401 Unauthorized

**Symptom:**
```
Status: 401
Response: { message: "Unauthorized" }
```

**Solution:**

1. **Verify auth token exists:**
   ```javascript
   // In console:
   localStorage.getItem('authToken')
   // Should show long JWT string starting with eyJ
   ```

2. **If no token, login first:**
   - Click "Login" button
   - Complete Cognito flow
   - Token should be stored

3. **Check token format:**
   ```javascript
   // Token should be sent as:
   Authorization: Bearer eyJ0eXAi...
   
   // NOT:
   Authorization: eyJ0eXAi...  // Missing "Bearer"
   Authorization: JWT eyJ0eXAi...  // Wrong prefix
   ```

4. **Check token expiration:**
   ```javascript
   // Decode token at https://jwt.io
   // Check "exp" field
   // If less than current time, token expired
   // Need to refresh or re-login
   ```

---

### API Call Returns 403 Forbidden

**Symptom:**
```
Status: 403
Response: { message: "Forbidden" }
```

**Solution:**

1. **Check IAM permissions:**
   - Backend Lambda needs DynamoDB access
   - See CDK stack configuration

2. **Check user permissions:**
   - User authenticated but not authorized for resource
   - E.g., trying to access another user's application

3. **Check resource exists:**
   - Application ID might be invalid
   - See `verification.md` → Test 5

---

### API Call Returns 500 Internal Server Error

**Symptom:**
```
Status: 500
Response: { message: "Internal Server Error" }
```

**Solution:**

1. **Check backend logs:**
   ```bash
   aws logs tail /aws/lambda/careervp-handler --follow
   ```

2. **Common causes:**
   - Database connection failed
   - S3 access error
   - Lambda timeout (>15 minutes)
   - Missing environment variable

3. **Check CloudWatch for errors:**
   - AWS Console → CloudWatch → Logs
   - Look for Lambda error logs

---

## Authentication Issues

### Login Redirects to Cognito But Then Shows Error

**Symptom:** Cognito login page shows error like:
```
Invalid client id
or
Unauthorized client
```

**Solution:**

1. **Verify client ID:**
   ```
   Configured: 7blipbarsisbctqh6hlsj46sqa
   Frontend: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID
   ```

2. **Check Cognito console:**
   - User Pool → App Clients
   - Verify client exists with that ID
   - Check "Enabled" status

3. **Check client settings:**
   - Authentication flows enabled
   - Callback URLs configured
   - Allowed origins configured

See `cognito-config.md` for full setup.

---

### Token Not Stored After Login

**Symptom:**
1. Login succeeds
2. Redirected back to Amplify domain
3. localStorage.getItem('authToken') returns null

**Solution:**

1. **Check callback URL handling:**
   - Frontend code should extract token from URL
   - Look for file: `src/frontend/app/auth/callback.tsx` or similar

2. **Verify callback redirect works:**
   - After login, watch URL in browser address bar
   - Should show: `https://main.d123abc.amplifyapp.com/callback?code=xxx`
   - Then redirect to dashboard

3. **Check localStorage access:**
   ```javascript
   // In console:
   localStorage.setItem('test', 'value')
   localStorage.getItem('test')  // Should return 'value'
   ```

4. **Check for errors in callback handler:**
   - DevTools → Console
   - Look for errors during callback processing

---

### Logout Not Working

**Symptom:** Click logout, nothing happens or page reloads

**Solution:**

1. **Verify logout URL:**
   - Cognito console
   - User Pool → App Clients
   - Check "Allowed sign-out URLs" includes current domain

2. **Check logout button implementation:**
   ```typescript
   const handleLogout = () => {
     localStorage.removeItem('authToken');  // Remove token
     window.location.href = '...logout...'; // Redirect to Cognito
   };
   ```

3. **Verify token removed:**
   ```javascript
   // After logout:
   localStorage.getItem('authToken')  // Should return null
   ```

---

## Performance Issues

### High API Latency (>2 seconds)

**Symptom:** API calls take 2-5 seconds to respond

**Solution:**

1. **Check backend performance:**
   ```bash
   # Get Lambda metrics
   aws lambda get-function --function-name careervp-handler \
     --query 'Configuration.Timeout' --region us-east-1
   ```

2. **Check database performance:**
   - AWS Console → DynamoDB → Tables
   - Check "Consumed write/read capacity"
   - Look for throttling

3. **Check network latency:**
   - `ping 4xe2tdq8z6.execute-api.us-east-1.amazonaws.com`
   - Should be <100ms

4. **Add request tracing:**
   - AWS X-Ray can show bottlenecks
   - Enable in Lambda console

---

### High Memory Usage

**Symptom:** Browser tab uses 500+ MB memory

**Solution:**

1. **Check for memory leaks:**
   - DevTools → Memory tab
   - Take heap snapshot
   - Look for growing memory over time

2. **Check for infinite loops:**
   - DevTools → Sources tab
   - Set breakpoint
   - Step through code

3. **Check for large data structures:**
   - Look for arrays with thousands of items
   - Paginate results instead

---

### Bundle Size Too Large

**Symptom:** Page takes >5 seconds to load, bundle.js >2MB

**Solution:**

```bash
# Analyze bundle
npm install --save-dev @next/bundle-analyzer

# Add to next.config.js:
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
})
module.exports = withBundleAnalyzer(module.exports)

# Run:
ANALYZE=true npm run build

# Look for large dependencies to remove
```

---

## DNS & Domain Issues

### Custom Domain Shows 404

**Symptom:** `https://dev.careervp.com` returns 404

**Solution:**

1. **Verify DNS is propagated:**
   ```bash
   nslookup dev.careervp.com
   # Should return Amplify CloudFront address
   ```

2. **Check Route53 records:**
   - AWS Console → Route53 → Hosted Zones
   - Verify `dev.careervp.com` A record points to Amplify

3. **Wait for DNS propagation:**
   - Can take 24-48 hours
   - Check with `nslookup` periodically

4. **Verify SSL certificate:**
   - Amplify Console → Domain management
   - Certificate should be "Valid" (not "Pending")
   - Wait up to 30 minutes for validation

See `dns-migration.md` for custom domain setup.

---

## Git & Deployment Issues

### Wrong Branch Deployed

**Symptom:** Pushed to `develop`, but `main` was deployed

**Solution:**

1. **Check Amplify connected branches:**
   - Amplify Console → Settings → Connected branches
   - Verify branch is connected

2. **Check branch protection:**
   - GitHub → Settings → Branch protection rules
   - `main` might require review before auto-deploy

3. **Manual redeploy:**
   - Amplify Console → Deployments
   - Click **"Redeploy"** on correct commit

---

### Deployment Triggered But Git Push Didn't Go Through

**Symptom:** Push fails but Amplify still deploying

**Solution:**

1. **Check git status:**
   ```bash
   git status
   # Should show: "nothing to commit"
   ```

2. **Force push (only if needed):**
   ```bash
   git push --force origin branch-name
   ```

3. **Check Amplify webhook:**
   - GitHub → Settings → Webhooks
   - Verify Amplify webhook is active

---

## Getting Help

If issue not listed above:

1. **Check Amplify logs:**
   - Amplify Console → Deployments → Click deployment → View logs

2. **Check CloudWatch logs:**
   - AWS Console → CloudWatch → Logs
   - Search by Lambda function name

3. **Check GitHub issues:**
   - Next.js issues: https://github.com/vercel/next.js/issues
   - AWS Amplify issues: https://github.com/aws-amplify/amplify-js/issues

4. **Contact support:**
   - Email: ymeirovich@gmail.com
   - Include: Error message, steps to reproduce, deployment URL

---

**Status:** Common issues covered
**Update frequency:** Add issues as discovered
**Escalation:** Contact support if issue persists
