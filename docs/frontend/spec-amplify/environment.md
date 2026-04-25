# Environment Configuration

Environment variables for each deployment branch (dev, stage, prod).

## Overview

Three environments, each with distinct configuration:

| Environment | Branch | Domain | API Endpoint | Cognito Pool | Deployment |
|------------|--------|--------|--------------|--------------|------------|
| **Development** | `develop` | dev.careervp.com | dev-api | us-east-1_WiHMRqLpe | Auto |
| **Staging** | `stage` | stage.careervp.com | prod-api | us-east-1_WiHMRqLpe | Auto |
| **Production** | `main` | app.careervp.com | prod-api | us-east-1_WiHMRqLpe | Auto |

**Note:** All three environments currently use the same Cognito pool and backend API. In future, could separate dev/stage from prod.

---

## Environment Variables

All environments share the same variables (for now). When custom domains are ready, update Amplify environment variables per branch.

### Required Variables

```bash
# All environments use same values
NEXT_PUBLIC_API_URL="https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod"
NEXT_PUBLIC_COGNITO_USER_POOL_ID="us-east-1_WiHMRqLpe"
NEXT_PUBLIC_COGNITO_CLIENT_ID="7blipbarsisbctqh6hlsj46sqa"
NEXT_PUBLIC_COGNITO_REGION="us-east-1"
```

### Optional Variables (Future)

When you want environment-specific behavior:

```bash
# Dev-specific (logs, debug mode)
NEXT_PUBLIC_DEBUG_MODE="true"
NEXT_PUBLIC_LOG_LEVEL="debug"

# Prod-specific (tracking, analytics)
NEXT_PUBLIC_ANALYTICS_ID="google-tag-manager-id"
NEXT_PUBLIC_SENTRY_DSN="https://..."
```

---

## Setting Variables in Amplify

### Method 1: Amplify Console (Recommended)

1. Go to **Amplify Console** → **App settings** → **Environment variables**
2. Select branch dropdown (if branch-specific)
3. Click **"Add environment variable"**
4. Enter:
   - **Key:** `NEXT_PUBLIC_API_URL`
   - **Value:** `https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod`
5. Click **"Save"**

Repeat for each variable.

### Method 2: AWS CLI

```bash
# List current variables
aws amplify get-app --app-id <APP_ID> --region us-east-1

# Add variable (via CLI not directly supported, use console)
```

### Method 3: Amplify Configuration File

Create `amplify.yml` in `src/frontend/`:

```yaml
version: 1
env:
  # These variables available during build
  NEXT_PUBLIC_API_URL: https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod
  NEXT_PUBLIC_COGNITO_USER_POOL_ID: us-east-1_WiHMRqLpe
  NEXT_PUBLIC_COGNITO_CLIENT_ID: 7blipbarsisbctqh6hlsj46sqa
  NEXT_PUBLIC_COGNITO_REGION: us-east-1

frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: .next
    files:
      - '**/*'
```

**Note:** Variables in `amplify.yml` are visible in git — keep secrets out.

---

## Local Development

### Development Setup

For local development with `npm run dev`:

Create `.env.local` (NOT committed to git):

```bash
NEXT_PUBLIC_API_URL="https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod"
NEXT_PUBLIC_COGNITO_USER_POOL_ID="us-east-1_WiHMRqLpe"
NEXT_PUBLIC_COGNITO_CLIENT_ID="7blipbarsisbctqh6hlsj46sqa"
NEXT_PUBLIC_COGNITO_REGION="us-east-1"
```

**Verify `.env.local` is in `.gitignore`:**

```bash
# .gitignore should contain:
.env.local
.env.*.local
```

### Run Locally

```bash
cd src/frontend

# Create .env.local with values above
echo "NEXT_PUBLIC_API_URL=..." > .env.local

# Start dev server
npm run dev

# Access at http://localhost:3000
```

---

## Configuration by Environment

### Development (develop branch)

**Current URL:** `https://develop.d123abc.amplifyapp.com`
**Future URL:** `https://dev.careervp.com` (after DNS propagates)

**Purpose:** Daily development, testing, integration

**Settings:**
```bash
NEXT_PUBLIC_API_URL="https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod"
NEXT_PUBLIC_COGNITO_USER_POOL_ID="us-east-1_WiHMRqLpe"
NEXT_PUBLIC_COGNITO_CLIENT_ID="7blipbarsisbctqh6hlsj46sqa"
NEXT_PUBLIC_COGNITO_REGION="us-east-1"
```

**Deployment:**
- Automatic on each push to `develop`
- Build logs visible in Amplify console
- Rollback available

### Staging (stage branch)

**Current URL:** `https://stage.d123abc.amplifyapp.com`
**Future URL:** `https://stage.careervp.com` (after DNS propagates)

**Purpose:** Pre-production testing, QA validation

**Settings:** Same as development (for now)
```bash
NEXT_PUBLIC_API_URL="https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod"
```

**Deployment:**
- Automatic on each push to `stage`
- Must pass all tests before promoting to prod
- Customer may access for UAT

### Production (main branch)

**Current URL:** `https://main.d123abc.amplifyapp.com`
**Future URL:** `https://app.careervp.com` (when domain defined)

**Purpose:** Live, production deployment

**Settings:** Same as development (for now)
```bash
NEXT_PUBLIC_API_URL="https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod"
```

**Deployment:**
- Automatic on each push to `main`
- Or manual deploy via Amplify console
- Requires code review (branch protection)
- Monitored closely for errors

---

## Handling Secrets

### ✅ Safe: Public Variables in NEXT_PUBLIC_*

These are visible in browser DevTools:
```javascript
// OK to be public:
NEXT_PUBLIC_API_URL="https://api.careervp.com"
NEXT_PUBLIC_COGNITO_USER_POOL_ID="us-east-1_WiHMRqLpe"
NEXT_PUBLIC_COGNITO_CLIENT_ID="7blipbarsisbctqh6hlsj46sqa"
```

### ❌ Never: Secrets in Environment Variables

Never put in ANY environment variable (public or private):
- ❌ Cognito client secret
- ❌ Database passwords
- ❌ Private API keys
- ❌ AWS credentials
- ❌ Encryption keys

These should be handled by backend (Lambda functions).

### ✅ Safe: Secrets in AWS Secrets Manager

If frontend needs a secret for build-time only:

1. Store in AWS Secrets Manager
2. Reference in Amplify build process
3. Secret injected during build, not committed to git

```yaml
# amplify.yml
build:
  commands:
    - export API_KEY=$(aws secretsmanager get-secret-value --secret-id api-key --query SecretString --output text)
    - npm run build
```

---

## Updating Variables

### To Add a New Variable

1. **Decide:** Is this variable environment-specific or shared?
   - Shared: Add to Amplify console for all branches
   - Specific: Add only to that branch

2. **Add to Amplify:**
   - Amplify Console → Environment Variables
   - Key + Value
   - Click Save

3. **Update Code (if using):**
   ```typescript
   const apiUrl = process.env.NEXT_PUBLIC_API_URL;
   ```

4. **Deploy:**
   - Amplify auto-redeploys on save
   - Or push to Git to trigger build

### To Change an Existing Variable

1. **Amplify Console** → **Environment Variables**
2. **Select variable** → **Edit**
3. **Update value**
4. **Save** → Auto-redeploy

**Note:** No git commit needed for Amplify variables

### To Remove a Variable

1. **Amplify Console** → **Environment Variables**
2. **Select variable** → **Delete**
3. **Save** → Auto-redeploy

---

## Validation

### Verify Variables Set Correctly

In browser console after loading site:

```javascript
// Check if variable is available
console.log(process.env.NEXT_PUBLIC_API_URL)
// Should output: https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod

// Check in page source:
// Right-click → View Page Source → Search for API_URL
// Should see value in JavaScript somewhere
```

### Verify Variables in Build Logs

In Amplify Console:

1. Go to **Deployments** tab
2. Click a deployment
3. Scroll to build logs
4. Look for:
   ```
   NEXT_PUBLIC_API_URL=https://...
   NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_WiHMRqLpe
   ```

---

## Future: Environment-Specific Backends

When backend is split by environment:

### Development API
```
https://dev-api.careervp.com/prod
```

Update `.env.local`:
```bash
NEXT_PUBLIC_API_URL="https://dev-api.careervp.com/prod"
```

### Staging API
```
https://stage-api.careervp.com/prod
```

Update Amplify for `stage` branch:
```bash
NEXT_PUBLIC_API_URL="https://stage-api.careervp.com/prod"
```

### Production API
```
https://api.careervp.com/prod
```

Update Amplify for `main` branch:
```bash
NEXT_PUBLIC_API_URL="https://api.careervp.com/prod"
```

---

## Troubleshooting

### Variable Not Being Used

1. Verify variable name starts with `NEXT_PUBLIC_`
2. Restart dev server (if local)
3. Clear browser cache (Ctrl+Shift+Delete)
4. Check DevTools → Application → Local Storage (clear if persisted)

### Variable Shows as undefined

1. Amplify Console → Environment Variables
2. Verify variable is set for the correct branch
3. Check spelling exactly
4. Wait for redeploy to complete

### Old Value Still Used

1. CloudFront cache: Wait 10 minutes or manually invalidate
   ```bash
   aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
   ```
2. Browser cache: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
3. CDN cache: Amplify auto-invalidates, but may take minutes

---

**Status:** Ready to configure
**Update frequency:** Change as needed via Amplify console
**Rollback:** Previous deployments cached (Amplify Console → Deployments)
