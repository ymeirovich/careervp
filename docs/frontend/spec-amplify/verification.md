# Deployment Verification Checklist

Complete testing checklist to verify frontend is fully functional.

## Pre-Verification Setup

Before starting tests:

- [ ] Get Amplify CloudFront URL from Amplify Console
  - Example: `https://main.d123abc.amplifyapp.com`
- [ ] Backend CORS updated (see `backend-cors.md`)
- [ ] Cognito callbacks updated (see `cognito-config.md`)
- [ ] Open browser DevTools (F12 or Cmd+Option+I)

---

## Test 1: Page Load

### Test: Dashboard Loads Without Errors

1. Open `https://main.d123abc.amplifyapp.com` in browser
2. Page should load in <3 seconds
3. Dashboard should be visible

**Verify:**
- [ ] No white screen or loading spinner (after 3 sec)
- [ ] Console shows no red errors (DevTools → Console tab)
- [ ] Network tab shows 200 responses for HTML, CSS, JS

**If fails:**
- See `troubleshooting.md` → "Page Load Issues"

---

## Test 2: Application List (API Call)

### Test: Applications List Loads from Backend

1. Scroll down on dashboard
2. Look for "Applications" section or list
3. Should show applications or "No applications" message

**Verify:**
- [ ] Application list renders (not blank or error)
- [ ] DevTools → Network tab shows:
  - `GET https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/applications`
  - Status: `200` (or `401` if not logged in — expected)
- [ ] No CORS errors in Console

**Expected responses:**
```javascript
// If logged in:
Status: 200
Response: [
  { id: "app1", name: "Application 1", ... },
  { id: "app2", name: "Application 2", ... }
]

// If not logged in:
Status: 401
Response: { message: "Unauthorized" }
```

**If fails:**
- See `troubleshooting.md` → "API Call Failures"
- Check `backend-cors.md` — CORS might not be deployed

---

## Test 3: CORS Headers

### Test: Backend Returns Correct CORS Headers

1. DevTools → Network tab
2. Click the API request: `/applications`
3. Go to "Response Headers" section
4. Look for CORS headers

**Expected headers:**
```
Access-Control-Allow-Origin: https://main.d123abc.amplifyapp.com
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET,POST,PUT,DELETE,PATCH,OPTIONS
```

**Verify:**
- [ ] `Access-Control-Allow-Origin` matches your domain
- [ ] `Access-Control-Allow-Credentials: true` is present
- [ ] Methods include `GET, POST, PUT, DELETE, OPTIONS`

**If fails:**
- Backend CORS not deployed yet
- See `backend-cors.md` → "Verify CORS Headers"

---

## Test 4: Authentication (Critical)

### Test 4.1: Login Redirect

1. Click **"Login"** button
2. Page should redirect to Cognito login
3. URL bar should show: `https://<cognito-domain>.auth.us-east-1.amazoncognito.com/...`

**Verify:**
- [ ] Redirected to Cognito domain
- [ ] URL includes `redirect_uri=https://main.d123abc.amplifyapp.com/callback`
- [ ] Cognito login form appears

**If fails:**
- See `troubleshooting.md` → "Auth: Login Redirect"
- Check `cognito-config.md` — callback URLs might not be saved

### Test 4.2: Login Success

1. Enter valid Cognito credentials
2. Submit login form
3. Should redirect back to `https://main.d123abc.amplifyapp.com/callback`
4. Callback should complete and redirect to dashboard

**Verify:**
- [ ] Redirected back to Amplify domain
- [ ] Dashboard loads (not blank)
- [ ] DevTools → Application → Local Storage shows auth token:
  - Look for keys like: `authToken`, `access_token`, `idToken`
  - Value should be a long JWT string (e.g., `eyJ0eXAi...`)

**Expected token format:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

**If fails:**
- See `troubleshooting.md` → "Auth: Token Not Stored"
- Check `cognito-config.md` — callback URLs format

### Test 4.3: Auth Token in API Calls

1. While logged in, trigger an API call
   - Scroll dashboard to load applications
   - Or click a link that fetches data
2. DevTools → Network tab
3. Click API request (e.g., `/applications`)
4. Go to "Request Headers" section

**Expected headers:**
```
Authorization: Bearer eyJ0eXAi...
Content-Type: application/json
```

**Verify:**
- [ ] `Authorization: Bearer <token>` header present
- [ ] Token starts with `eyJ` (JWT format)
- [ ] API responds with 200 (not 401)

**If fails:**
- Frontend not sending auth token
- See `troubleshooting.md` → "Auth: Token Not Sent"

---

## Test 5: Application Detail Page

### Test: Navigate to Application & Load Details

1. On dashboard, click an application
2. Should navigate to `/applications/[id]`
3. Application details should load

**Verify:**
- [ ] URL changes to `/applications/abc123/` (some ID)
- [ ] Page loads without blank screen
- [ ] No red console errors
- [ ] Network tab shows successful API calls

**Expected API calls:**
```
GET /applications/{id}        → 200
GET /company-research/{id}    → 200 (if available)
GET /cv-tailored/{id}         → 200 (if available)
GET /vpr/{id}                 → 200 (if available)
```

**If fails:**
- See `troubleshooting.md` → "Dynamic Routes"

---

## Test 6: Generate Artifact (Full Flow)

### Test: Click "Generate" on an Artifact

1. On application detail page, find an artifact (e.g., "Company Research")
2. Click **"Research Company"** or **"Generate"** button
3. Should show loading spinner
4. After 10-30 seconds, result should appear

**Verify:**
- [ ] Loading spinner shows
- [ ] No error messages
- [ ] Result renders (text, cards, sections)
- [ ] Network tab shows:
  - `POST /company-research` → 200 or 202 (accepted)
  - Subsequent `GET /company-research/{id}` → 200

**If fails:**
- See `troubleshooting.md` → "Generation Issues"

---

## Test 7: Logout

### Test: Logout Flow

1. Click **"Logout"** button
2. Should redirect to Cognito logout endpoint
3. Should be redirected back to home page
4. Auth token should be removed from localStorage

**Verify:**
- [ ] Redirected away from dashboard
- [ ] URL shows home page or login page
- [ ] DevTools → Application → Local Storage:
  - `authToken` should be gone
  - Or token should be empty
- [ ] Clicking a protected page redirects to login

**If fails:**
- See `troubleshooting.md` → "Auth: Logout Issues"

---

## Test 8: Performance Metrics

### Test: Page Load Speed

1. Open `https://main.d123abc.amplifyapp.com` in fresh browser
2. DevTools → Performance tab
3. Reload page
4. Wait for page to fully load

**Verify:**
- [ ] First Contentful Paint (FCP) < 3 seconds
- [ ] Largest Contentful Paint (LCP) < 5 seconds
- [ ] Cumulative Layout Shift (CLS) < 0.1
- [ ] Total JS bundle size < 2 MB

**Expected metrics:**
```
FCP: 2-3 seconds (Amplify + CloudFront)
LCP: 3-4 seconds (Amplify + CloudFront)
CLS: 0.01-0.05 (good)
Bundle: 500 KB - 1.5 MB
```

**If slower:**
- Normal for first deploy (CloudFront cache warming)
- Subsequent loads should be faster
- See `troubleshooting.md` → "Performance Issues"

---

## Test 9: HTTPS & Security

### Test: All Traffic is HTTPS

1. Open DevTools → Network tab
2. Look at all requests
3. All should start with `https://` (not `http://`)

**Verify:**
- [ ] No mixed content warnings
- [ ] All API calls use `https://`
- [ ] Cognito redirect uses `https://`
- [ ] No console warnings about insecure content

**If fails:**
- Check `next.config.js` for hardcoded `http://` URLs
- Check environment variables don't have `http://`

---

## Test 10: Different Browsers & Devices

### Test: Cross-Browser Compatibility

Test on:
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)

**Verify:** All tests 1-9 pass on each browser

### Test: Responsive Design

1. Resize browser window
2. DevTools → Device toolbar (mobile view)
3. Test on:
   - [ ] Desktop (1920×1080)
   - [ ] Tablet (768×1024)
   - [ ] Mobile (375×667)

**Verify:**
- [ ] Layout adapts to screen size
- [ ] No horizontal scrolling on mobile
- [ ] Touch interactions work on mobile
- [ ] Text is readable on all sizes

---

## Summary Checklist

### Phase 1: Basic Functionality
- [ ] Page loads without errors
- [ ] Application list displays
- [ ] CORS headers present
- [ ] No console errors

### Phase 2: Authentication
- [ ] Login redirect works
- [ ] Token stored after login
- [ ] Token sent with API requests
- [ ] Logout clears token

### Phase 3: API Integration
- [ ] API calls successful (200 status)
- [ ] Application details load
- [ ] Generate artifact works
- [ ] Data displays correctly

### Phase 4: Performance & Security
- [ ] Page load fast (<5 seconds)
- [ ] All traffic HTTPS
- [ ] No mixed content warnings
- [ ] Responsive on all devices

### Phase 5: Cross-Browser
- [ ] Works on Chrome, Firefox, Safari
- [ ] Works on desktop, tablet, mobile
- [ ] No console errors on any device

---

## If All Tests Pass ✅

Deployment is **SUCCESSFUL**. Next steps:

1. **Custom domains** (future) → See `dns-migration.md`
2. **Production hardening** → See `security-checklist.md`
3. **Performance optimization** → See `troubleshooting.md`

---

## If Any Test Fails ❌

See `troubleshooting.md` for specific issue.

---

**Status:** Ready to verify
**Estimated time:** 30 minutes
**Success criteria:** All 10 tests pass
