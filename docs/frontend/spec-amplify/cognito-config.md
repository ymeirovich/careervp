# Cognito Authentication Configuration

Configure Amazon Cognito User Pool callback URLs for Amplify frontend.

## Problem

Without proper callback URLs, Cognito auth fails:
```
Error: redirect_uri mismatch
The provided redirect_uri is not registered with the client
```

## Solution: Update Cognito App Client

### Current State

Your Cognito User Pool is configured:
- **Pool ID:** `us-east-1_WiHMRqLpe`
- **Client ID:** `7blipbarsisbctqh6hlsj46sqa`
- **Region:** us-east-1

**But:** Callback URLs probably don't include Amplify domain.

### Required Changes

Add callback URLs for:
1. **Amplify CloudFront** (immediate, for testing)
2. **Custom domains** (future, after DNS propagates)
3. **Localhost** (local development)

Also add sign-out URLs for logout functionality.

---

## Step 1: Navigate to Cognito Console

```
https://us-east-1.console.aws.amazon.com/cognito/v2/
```

1. Click **"User pools"** (left sidebar)
2. Select **`careervp-pool`** (your user pool)
3. Click **"App integration"** (left sidebar)
4. Click **"App clients and analytics"**
5. Select the app client: `7blipbarsisbctqh6hlsj46sqa`

---

## Step 2: Update Allowed Callback URLs

### Current Callbacks

You likely see:
```
https://careervp.com/callback
https://localhost:3000/callback
```

### Required Callbacks

Replace with this list (all three are needed):

```
https://main.d123abc.amplifyapp.com/callback
https://develop.d123abc.amplifyapp.com/callback
https://stage.d123abc.amplifyapp.com/callback
https://app.careervp.com/callback
https://dev.careervp.com/callback
https://stage.careervp.com/callback
http://localhost:3000/callback
```

### How to Update

1. In Cognito console, find **"Allowed callback URLs"** field
2. Clear existing values
3. Paste all 7 URLs (one per line or space-separated, depending on UI)
4. Click **"Save changes"**

---

## Step 3: Update Allowed Sign-Out URLs

Users need to be able to log out.

### Required Sign-Out URLs

```
https://main.d123abc.amplifyapp.com/
https://develop.d123abc.amplifyapp.com/
https://stage.d123abc.amplifyapp.com/
https://app.careervp.com/
https://dev.careervp.com/
https://stage.careervp.com/
http://localhost:3000/
```

### How to Update

1. In Cognito console, find **"Allowed sign-out URLs"** field
2. Clear existing values
3. Paste all 7 URLs
4. Click **"Save changes"**

---

## Step 4: Verify Configuration

### Check Allowed Origins (CORS)

Cognito also has CORS settings for the authorization endpoint:

1. In Cognito console, go to **"Domain"** section
2. Find **"Allowed origins"**
3. Add the same Amplify domains:
   ```
   https://main.d123abc.amplifyapp.com
   https://develop.d123abc.amplifyapp.com
   https://stage.d123abc.amplifyapp.com
   https://app.careervp.com
   https://dev.careervp.com
   https://stage.careervp.com
   http://localhost:3000
   ```

---

## Step 5: Test Authentication Flow

1. Open Amplify CloudFront URL: `https://main.d123abc.amplifyapp.com`
2. Click **"Login"** button
3. Should redirect to Cognito login page
4. **DO NOT login yet** — first verify URL is correct
5. URL should show: `https://<cognito-domain>.auth.us-east-1.amazoncognito.com/oauth2/authorize?...&redirect_uri=https://main.d123abc.amplifyapp.com/callback`
6. If URL is missing or incorrect, Cognito rejects it

If redirect fails:
- Check callback URLs were saved (refresh Cognito console)
- Clear browser cache
- Try incognito window

---

## Step 6: Complete Auth Flow Test

Once callback URL works:

1. Enter Cognito login credentials
2. Should be redirected back to `https://main.d123abc.amplifyapp.com/callback`
3. Frontend should handle redirect and store auth token
4. Dashboard should show authenticated state
5. Should see username in profile/settings

If auth token not stored:
- Check browser localStorage/cookies
- See `troubleshooting.md` → "Auth Issues"

---

## Frontend Implementation

Your frontend likely already implements Cognito auth. Verify these exist:

### In Frontend Code

**Check `src/frontend/app/auth/` or similar:**
```typescript
// Should handle Cognito redirect_uri callback
const handleCallback = async () => {
  const code = new URLSearchParams(window.location.search).get('code');
  
  if (code) {
    // Exchange code for tokens
    const tokens = await cognito.getTokens(code);
    localStorage.setItem('authToken', tokens.access_token);
  }
};
```

**Verify login button redirects to Cognito:**
```typescript
const handleLogin = () => {
  const redirectUri = encodeURIComponent('https://main.d123abc.amplifyapp.com/callback');
  const cognitorDomain = 'careervp-pool-XXXX.auth.us-east-1.amazoncognito.com';
  
  window.location.href = `${cognitoDomain}/oauth2/authorize?...&redirect_uri=${redirectUri}`;
};
```

If not implemented, you'll need to add Cognito integration to frontend.

---

## Handling Future Domain Changes

### When app.careervp.com is Defined

Once production domain is set:

1. Return to Cognito console
2. Add `https://app.careervp.com/callback` to allowed callback URLs
3. Add `https://app.careervp.com/` to allowed sign-out URLs
4. Add `https://app.careervp.com` to allowed origins
5. Click **"Save changes"**

No frontend code changes needed — Amplify domain already added.

---

## Security Notes

### ✅ Best Practices

- **Explicit domains:** List each domain separately (not wildcards)
- **Callback URL format:** Must include full path (e.g., `/callback`)
- **HTTPS only:** Never use `http://` except for localhost
- **Test before prod:** Always test on dev domain before prod

### ⚠️ Do NOT

- ❌ Use wildcards: `https://*.amplifyapp.com` (security risk)
- ❌ Use `https://amplifyapp.com` (too broad)
- ❌ Forget protocol: `careervp.com` (must be `https://`)
- ❌ Skip sign-out URL (users can't logout cleanly)

### Token Storage Security

Frontend stores auth token — ensure it's protected:

```typescript
// ✅ SAFE: HTTP-only cookie (not accessible to JavaScript)
// This is ideal but requires backend cooperation

// ⚠️ ACCEPTABLE: localStorage with HTTPS-only domain
localStorage.setItem('authToken', token);
// Risk: XSS can steal tokens, but only on HTTPS

// ❌ AVOID: sessionStorage without encryption
// Risk: Visible in browser tools

// ❌ NEVER: Storing in browser globals or state
// Risk: XSS, debugging tools expose it
```

Your frontend currently uses localStorage — acceptable for production SPA.

---

## Troubleshooting

### "Invalid redirect_uri" Error

1. **Verify URL matches exactly:**
   ```
   Config:  https://main.d123abc.amplifyapp.com/callback
   Browser: https://main.d123abc.amplifyapp.com/callback
   ```
   (No extra slashes, query params, or variations)

2. **Check Cognito console:**
   - Refresh page (clear cache)
   - Verify callback URL saved
   - Copy/paste from config, don't type

3. **Try different browser/incognito:**
   - Browser cache may be stale

### "CORS error" at Login

This is different from redirect_uri error:

1. Check **Allowed origins** in Cognito Domain settings
2. Verify Amplify domain is listed
3. See `backend-cors.md` for CORS general troubleshooting

### Token Not Stored After Login

1. Open browser DevTools → Application → Local Storage
2. Look for key like `authToken` or `access_token`
3. If missing, frontend didn't extract token from redirect
4. Check frontend code handles Cognito callback

---

## Related Configuration

- **Backend CORS:** See `backend-cors.md` (API calls need CORS too)
- **Verification:** See `verification.md` → "Authentication"
- **Troubleshooting:** See `troubleshooting.md` → "Auth Issues"

---

**Status:** Ready to configure
**Time required:** 10 minutes
**Changes:** Cognito console only (no code changes)
**Rollback:** Easy — just remove URLs
