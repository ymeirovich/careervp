# Manual Steps Only (AWS Console & Browser)

This guide contains ONLY the manual steps you must perform in AWS console or browser.

**Automated parts** (code edits, CDK deployment, tests) are handled separately.

---

## Prerequisites

Before starting, have these ready:
- [ ] AWS account access (us-east-1)
- [ ] GitHub repo access
- [ ] Automation has completed (code changes committed)
- [ ] 30 minutes uninterrupted time

---

## STEP 1: Create Amplify App in AWS Console

**Time:** 5-10 minutes
**Location:** https://us-east-1.console.aws.amazon.com/amplify/apps

### 1.1 Start New App

1. Go to **AWS Amplify Console** (link above)
2. Click **"Create app"** (blue button, top right)
3. Select **"Host web app"**
4. Click **"Continue"**

### 1.2 Connect GitHub

1. Choose **GitHub** as source
2. Click **"Continue"**
3. Button appears: **"Authorize AWS Amplify on GitHub"**
4. Click it
5. GitHub login page appears
   - Sign in if needed
   - Review permissions
   - Click **"Authorize anthropics-deploy"** (or similar AWS app name)
6. Back to Amplify → GitHub authorization complete

### 1.3 Select Repository

1. **Repository dropdown** → Select `careervp` (your GitHub repo)
2. **Branch dropdown** → Select `main`
3. Click **"Next"**

### 1.4 Configure Build Settings

Amplify auto-detects Next.js. You should see:

```
App name: careervp-frontend  ✓
Build command: npm run build  ✓
Build output directory: .next  ✓
```

**Leave these as-is.** Click **"Save and deploy"**

**⏳ Wait:** Initial deployment starts (~5 minutes)

---

## STEP 2: Get Your Amplify CloudFront URL

**Time:** 1-2 minutes
**Important:** You'll need this URL for CORS and Cognito configuration

### 2.1 Wait for Deployment

In Amplify Console:
1. Go to **"Deployments"** tab
2. Watch the status:
   ```
   "Building..." → "Verifying..." → "Hosting..."
   ```
3. When status shows **"Hosted"**, deployment complete (~3-5 min)

### 2.2 Copy CloudFront URL

1. Go to **"Deployments"** tab
2. Look at the top deployment
3. Find the "Domain" column
4. **Copy this URL:**
   ```
   https://main.d123abc.amplifyapp.com
   ```
   (Your `d123abc` will be different — unique to your Amplify app)
https://front-ui-update-amplify1.d3j2wnm8g5clnw.amplifyapp.com
### 2.3 Save for Next Steps

**Save this URL in a text editor or notepad:**
```
Amplify CloudFront URL: https://main.d123abc.amplifyapp.com
```

You'll use this in:
- STEP 3: Cognito callbacks (automated — but you provide the URL)
- STEP 4: Browser testing

**Do not continue until you have this URL.**

---

## STEP 3: Wait for Automated Backend Deployment

**Time:** 10-15 minutes (hands-off)
**What's happening:** Automation is updating backend CORS to allow your CloudFront domain

### 3.1 Monitor Backend Deployment

Automation will:
1. Edit `infra/careervp/service_stack.py` (add your CloudFront URL to CORS)
2. Commit changes to Git
3. Run `cdk deploy` to update API Gateway CORS

**You don't need to do anything — just wait.**

### 3.2 Verify Backend Deployed

When automation completes, you'll see:
```
Stack update complete
✓ CareerVpCrudDev deployed
```

**Check:** AWS CloudFormation console (to verify)
1. Go to https://us-east-1.console.aws.amazon.com/cloudformation
2. Look for stack: `CareerVpCrudDev`
3. Status should be **"UPDATE_COMPLETE"** (green)

If status is something else, contact support.

---

## STEP 4: Update Cognito Callbacks (Critical!)

**Time:** 5 minutes
**Location:** AWS Cognito Console
**Importance:** Without this, login will fail with "redirect_uri mismatch"

### 4.1 Open Cognito Console

Go to: https://us-east-1.console.aws.amazon.com/cognito/v2/

1. Click **"User pools"** (left sidebar)
2. Find **`careervp-pool`** in the list
3. Click on it

### 4.2 Find App Client Settings

1. In left sidebar, click **"App integration"**
2. Click **"App clients and analytics"**
3. Find client ID: `7blipbarsisbctqh6hlsj46sqa`
4. Click on it

### 4.3 Update Allowed Callback URLs

You should see a section: **"Allowed callback URLs"**

**Current value** (probably):
```
https://careervp.com/callback
https://localhost:3000/callback
```

**Replace with all 7 URLs** (copy/paste exactly):
```
https://main.d123abc.amplifyapp.com/callback
https://develop.d123abc.amplifyapp.com/callback
https://stage.d123abc.amplifyapp.com/callback
https://app.careervp.com/callback
https://dev.careervp.com/callback
https://stage.careervp.com/callback
http://localhost:3000/callback
```

**Replace `d123abc` with YOUR CloudFront subdomain** (from STEP 2)

### 4.4 Update Allowed Sign-Out URLs

Find section: **"Allowed sign-out URLs"**

**Replace with all 7 URLs**:
```
https://main.d123abc.amplifyapp.com/
https://develop.d123abc.amplifyapp.com/
https://stage.d123abc.amplifyapp.com/
https://app.careervp.com/
https://dev.careervp.com/
https://stage.careervp.com/
http://localhost:3000/
```

**Again, replace `d123abc` with YOUR CloudFront subdomain**

### 4.5 Update Allowed Origins (CORS)

Scroll down to find: **"Domain"** section

Look for: **"Allowed origins"** field

**Add all 7 origins**:
```
https://main.d123abc.amplifyapp.com
https://develop.d123abc.amplifyapp.com
https://stage.d123abc.amplifyapp.com
https://app.careervp.com
https://dev.careervp.com
https://stage.careervp.com
http://localhost:3000
```

### 4.6 Save Changes

1. Scroll to bottom
2. Click **"Save"** (blue button)
3. Wait for confirmation: "Settings have been saved"

**Important:** If you don't see "Save" button, you may need to scroll in the form.

---

## STEP 5: Test in Browser (Verification)

**Time:** 20 minutes
**What:** Verify frontend loads, API works, auth flow succeeds

### 5.1 Open Amplify URL

1. Open new browser tab
2. Go to: `https://main.d123abc.amplifyapp.com` (YOUR CloudFront URL)
3. **Wait** for page to load (should take <5 seconds)

**Verify:**
- [ ] Dashboard displays (no blank white screen)
- [ ] Navigation visible (top bar)
- [ ] No red console errors (open DevTools → Console)

### 5.2 Check Application List (API Call)

1. On dashboard, scroll down
2. Look for "Applications" section or list
3. Should show:
   - "No applications" (if user new), OR
   - List of applications (if user has data)

**Verify:**
- [ ] Section renders (not blank)
- [ ] No CORS errors in DevTools → Console
- [ ] DevTools → Network tab shows:
  - Request: `https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/applications`
  - Status: `401` or `200` (either OK — 401 means not logged in, which is fine for test)

**If you see CORS error:**
- Backend CORS not deployed yet
- Wait 5 minutes and refresh (F5)
- Then check again

### 5.3 Test Login (Auth Flow)

1. Click **"Login"** button (top right or center of page)
2. Page redirects to Cognito login
3. **Verify URL changes to:**
   ```
   https://<cognito-domain>.auth.us-east-1.amazoncognito.com/oauth2/authorize?...
   ```

4. **Login with credentials:**
   - Username: (your test user)
   - Password: (your test password)
   - Click "Sign In"

5. **Wait** for redirect (10-15 seconds)

**Verify:**
- [ ] Cognito login form appears
- [ ] Login succeeds
- [ ] Redirected back to `https://main.d123abc.amplifyapp.com`
- [ ] Dashboard shows you're logged in (name, avatar, etc.)

**If redirect fails with "redirect_uri mismatch":**
- Go back to STEP 4
- Verify Cognito callback URLs are saved (refresh Cognito console)
- Check URL format exactly matches (no typos)

### 5.4 Test API Call with Auth Token

While logged in:

1. Open DevTools (F12)
2. Go to **"Application"** tab (or "Storage")
3. Click **"Local Storage"** → Your domain
4. Look for `authToken` or `access_token` key
5. Value should be a long string starting with `eyJ`

**Example:**
```
Key: authToken
Value: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM...
```

### 5.5 Test API Call Network Request

While logged in:

1. DevTools → **"Network"** tab
2. Trigger an API call:
   - Scroll dashboard (loads applications)
   - Or click on an application link
3. Look for request to backend API:
   ```
   https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/...
   ```
4. Click the request
5. Go to **"Request Headers"** section
6. **Verify** you see:
   ```
   Authorization: Bearer eyJ0eXAi...
   ```

### 5.6 Check Response Status

Still in Network tab, same API request:

1. Go to **"Response"** section
2. Status should be **`200`** (green)
3. Response should show JSON data (application list, details, etc.)

**If you see:**
- `401` — Not authorized, login didn't work
- `403` — Forbidden, user doesn't have permission
- `500` — Backend error, contact support

### 5.7 Test Logout (Final Verification)

1. Click **"Logout"** button (usually top right or menu)
2. Redirected to Cognito logout or home page
3. Click back to Amplify URL
4. **Verify:**
   - [ ] Redirected to login page (or home page requires login)
   - [ ] Auth token removed from localStorage
   - [ ] Cannot see protected pages without re-login

---

## STEP 6: Confirm Deployment Success ✅

### 6.1 Summary Checklist

- [ ] Amplify app created
- [ ] CloudFront URL copied
- [ ] Backend CORS deployed (automated)
- [ ] Cognito callbacks updated
- [ ] Dashboard loads
- [ ] Application list renders (API call works)
- [ ] Login redirects to Cognito
- [ ] Auth token stored
- [ ] API calls include Bearer token
- [ ] Logout works

**If all checked:** Deployment is SUCCESSFUL ✅

**If any unchecked:** See "Troubleshooting" below

---

## Troubleshooting

### Page Shows Blank White Screen

1. **Wait 10 seconds** (sometimes slow to load)
2. **Hard refresh:** Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
3. **Check console:** DevTools → Console tab
4. Look for red error messages
5. If error mentions "CORS", see "CORS Error" below

**If still blank after 30 seconds:**
- Check Amplify Console → Deployments
- Verify status is "Hosted" (not still building)
- If building, wait for completion

### CORS Error at API Call

**Error message:**
```
CORS error: Access to XMLHttpRequest at 'https://4xe2tdq8z6...' 
from origin 'https://main.d123abc.amplifyapp.com' has been blocked
```

**Solution:**
1. Backend CORS not deployed yet
2. **Wait 5 minutes** (automation still deploying)
3. **Hard refresh browser** (Ctrl+Shift+R)
4. Try API call again
5. If still fails after 15 minutes, contact support

### "redirect_uri mismatch" at Login

**Error message:**
```
redirect_uri mismatch: 
The redirect_uri is not registered with the client
```

**Solution:**
1. Return to Cognito console (STEP 4)
2. Click "Allowed callback URLs" section
3. **Verify it was saved:**
   - Close and reopen the section
   - Should still show all 7 URLs
4. **Check URL format:**
   - Must include `/callback` at end
   - No extra slashes or spaces
   - Protocol must be `https://` (except localhost)
5. If changed, **click Save again**
6. Hard refresh browser (Ctrl+Shift+R)
7. Try login again

### Login Succeeds But Token Not Stored

1. Open DevTools → Application → Local Storage
2. Look for `authToken` key
3. **If missing:**
   - Frontend didn't extract token from redirect
   - This is a frontend code issue
   - Check `src/frontend/app/auth/` or similar for callback handler
4. **If present but empty:**
   - Token extraction failed
   - Same as above

### API Call Returns 401 Unauthorized

Means you're not logged in:

1. Login first (STEP 5.3)
2. **Verify token in localStorage** exists
3. **Verify Authorization header** sent (DevTools Network tab)
4. If token present but API still returns 401:
   - Token may be expired (check `exp` field in jwt.io)
   - Try logging out and back in

---

## What's Next?

After all tests pass ✅:

1. **Wait for DNS propagation** (24-48 hours)
   - Cloudflare adding NS records to Route53
   - Then dev.careervp.com will work

2. **Monitor deployment** (Week 1)
   - Check error rates
   - Monitor API latency
   - Watch logs in AWS CloudWatch

3. **Review security** (before production)
   - See `security-checklist.md`
   - Complete all checks
   - Get approval before going live

---

## Support

If you get stuck:

1. **Check troubleshooting** above first
2. **Check spec files** for detailed explanations
3. **Check AWS CloudWatch logs:**
   ```
   https://us-east-1.console.aws.amazon.com/cloudwatch
   ```
4. **Email support:** ymeirovich@gmail.com

---

**Status:** Ready for manual execution
**Estimated time:** 45-60 minutes (including waiting for automation)
**Next step:** Start with STEP 1 (Create Amplify App)
