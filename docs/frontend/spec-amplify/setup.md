# Amplify Setup Guide

Complete step-by-step instructions to deploy CareerVP frontend to AWS Amplify.

## Prerequisites Checklist

Before starting:
- [ ] AWS account with Amplify permissions (us-east-1)
- [ ] GitHub repo with write access
- [ ] Frontend code ready (next.config.js updated)
- [ ] Backend API accessible
- [ ] Cognito User Pool created
- [ ] 30 minutes of uninterrupted time

---

## Step 1: Prepare Codebase

### 1.1 Remove Static Export

**File:** `src/frontend/next.config.js`

```javascript
// REMOVE THIS LINE:
// output: 'export',

module.exports = {
  // Do NOT include output: 'export'
  
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
    NEXT_PUBLIC_COGNITO_USER_POOL_ID: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '',
    NEXT_PUBLIC_COGNITO_CLIENT_ID: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '',
    NEXT_PUBLIC_COGNITO_REGION: 'us-east-1',
  },
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};
```

**Verify:** Remove the line completely. Amplify will use Next.js default (`.next/` directory, server-side capable).

### 1.2 Test Build Locally

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/frontend

# Set environment variables
export NEXT_PUBLIC_API_URL="https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod"
export NEXT_PUBLIC_COGNITO_USER_POOL_ID="us-east-1_WiHMRqLpe"
export NEXT_PUBLIC_COGNITO_CLIENT_ID="7blipbarsisbctqh6hlsj46sqa"

# Clean build
rm -rf .next node_modules/.cache
npm run build
```

**Expected output:**
```
Route (app)                              Size     First Load JS
...
✓ Compiled successfully
```

**Verify:** Look for `.next/` directory (NOT `out/`), no build errors.

### 1.3 Commit Changes

```bash
cd /Users/yitzchak/Documents/dev/careervp

git add src/frontend/next.config.js
git commit -m "feat(frontend): prepare for Amplify deployment (remove static export)"
git push origin front/ui-update-v4-spec13  # or your current branch
```

---

## Step 2: Create Amplify App

### 2.1 Open AWS Amplify Console

```
https://us-east-1.console.aws.amazon.com/amplify/apps
```

### 2.2 Click "Create app"

1. Select **"Host web app"**
2. Choose **GitHub** as source
3. Click **"Continue"**

### 2.3 Authorize AWS to GitHub

1. Click **"Authorize AWS Amplify on GitHub"**
2. GitHub login (if needed)
3. Review permissions → **"Authorize"**

### 2.4 Select Repository & Branch

1. **Repository:** Select `careervp` (your GitHub repo)
2. **Branch:** Select `main` (or your deployment branch)
3. Click **"Next"**

**Note:** You'll configure multiple branches later for dev/stage/prod

### 2.5 Configure Build Settings

Amplify auto-detects Next.js. Accept defaults:
- **App name:** `careervp-frontend`
- **Build command:** `npm run build` ✅ (auto-detected)
- **Build output directory:** `.next` ✅ (auto-detected)
- **Environment variables:** Configure in Step 3

Click **"Save and deploy"** (deployment starts)

---

## Step 3: Configure Environment Variables

**During deployment, navigate to:** Amplify Console → App Settings → Environment Variables

### 3.1 Add Variables for Production (main branch)

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod` |
| `NEXT_PUBLIC_COGNITO_USER_POOL_ID` | `us-east-1_WiHMRqLpe` |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID` | `7blipbarsisbctqh6hlsj46sqa` |
| `NEXT_PUBLIC_COGNITO_REGION` | `us-east-1` |

**How to add:**
1. Go to **App Settings** → **Environment variables**
2. Click **"Add environment variable"**
3. Enter key/value
4. Click **"Save"**

**Note:** These apply to `main` branch. Dev/stage branches configured in Step 4.

---

## Step 4: Monitor Initial Deployment

### 4.1 Check Build Status

In Amplify Console:
1. Click **"Deployments"** tab
2. Watch for deployment progress
3. Build should complete in 3-5 minutes

### 4.2 Expected Build Log

```
▶ Building...
  - npm ci
  - npm run build
  - Compiling Next.js...
✓ Build successful
✓ Deployment successful to: https://main.d123abc.amplifyapp.com
```

**If build fails:** See `troubleshooting.md` → "Build Failures"

### 4.3 Get CloudFront URL

Once deployment succeeds:
1. Go to **Deployments** tab
2. Copy URL under "Domain": `https://main.d123abc.amplifyapp.com`
3. Test URL in browser
4. **Bookmark this URL** for testing

---

## Step 5: Configure Additional Branches (Dev & Stage)

### 5.1 Add Develop Branch (Dev Environment)

1. In Amplify Console → App Settings → **"Connected branches"**
2. Click **"Connect branch"**
3. Select **`develop`** (or dev branch name)
4. Click **"Connect"**

### 5.2 Set Dev Environment Variables

For `develop` branch, set:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod` |
| `NEXT_PUBLIC_COGNITO_USER_POOL_ID` | `us-east-1_WiHMRqLpe` |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID` | `7blipbarsisbctqh6hlsj46sqa` |
| `NEXT_PUBLIC_COGNITO_REGION` | `us-east-1` |

**How:**
1. Amplify Console → Environment Variables
2. Click branch dropdown → Select **`develop`**
3. Add variables (same as prod for now, can differ later)
4. **Save**

### 5.3 Add Stage Branch (Stage Environment)

Repeat 5.1-5.2 for `stage` branch if it exists.

### 5.4 View Branch Deployments

Each branch gets its own URL:
- `main` → `https://main.d123abc.amplifyapp.com`
- `develop` → `https://develop.d123abc.amplifyapp.com`
- `stage` → `https://stage.d123abc.amplifyapp.com`

---

## Step 6: Update Backend CORS (Critical!)

Your frontend will fail API calls until backend CORS is fixed.

**See:** `backend-cors.md` for detailed steps.

**Quick version:**
1. Edit `infra/careervp/service_stack.py`
2. Add Amplify CloudFront domain to `allow_origins`
3. Redeploy CDK

---

## Step 7: Update Cognito Callbacks (Critical!)

Your auth flow will fail until Cognito knows about the Amplify URL.

**See:** `cognito-config.md` for detailed steps.

**Quick version:**
1. AWS Cognito Console → User Pools → `careervp-pool` → App Clients
2. Add callback URLs:
   - `https://main.d123abc.amplifyapp.com/callback`
   - `https://develop.d123abc.amplifyapp.com/callback`
   - (etc. for stage)
3. **Save**

---

## Step 8: Test Deployment

See `verification.md` for complete testing checklist.

**Quick test:**
1. Open Amplify CloudFront URL
2. Dashboard loads without errors
3. Click login
4. Redirected to Cognito
5. Login succeeds
6. Redirected back to dashboard
7. Application list loads

If any step fails, see `troubleshooting.md`.

---

## Step 9: Prepare for Custom Domains (Future)

Once DNS propagation completes (24-48 hours):

1. Cloudflare will have NS records pointing to Route53
2. Return to Amplify Console
3. Click **"Domain management"**
4. Add custom domain: `dev.careervp.com`
5. SSL certificate auto-generated
6. Amplify updates Route53 records

See `dns-migration.md` for detailed custom domain setup.

---

## Rollback Plan

If deployment breaks production:

### Option A: Revert Git Commit
```bash
git revert <commit-hash>
git push main
# Amplify auto-redeploys from previous commit
```

### Option B: Disable Branch in Amplify
```
Amplify Console → Connected Branches → Disable Branch
```

### Option C: Restore from S3 (if backup exists)
```bash
aws s3 sync s3://careervp-frontend-dev-backup .
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
```

---

## Next Steps

1. ✅ Codebase prepared
2. ✅ Amplify app created
3. ✅ Environment variables set
4. ⏭️ **Backend CORS fixed** → See `backend-cors.md`
5. ⏭️ **Cognito callbacks updated** → See `cognito-config.md`
6. ⏭️ **Test end-to-end** → See `verification.md`

---

**Status:** Ready to deploy
**Estimated Time:** 30 minutes
**Blockers:** None if backend is accessible
