# Backend CORS Configuration

Configure API Gateway CORS to allow frontend calls from Amplify CloudFront distribution.

## Problem

Without CORS headers, browser blocks all API calls:
```
CORS error: Access to XMLHttpRequest at 'https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/...'
from origin 'https://main.d123abc.amplifyapp.com' has been blocked
```

## Solution: Update Backend CORS in CDK

### Current State

Check `infra/careervp/service_stack.py` for existing CORS configuration.

**Find this section:**
```python
api = apigw.RestApi(
    self, "CareervpApi",
    rest_api_name="careervp-api",
    # ... other config
    cors=apigw.CorsOptions(
        allow_origins=[...],  # ← This needs updating
        allow_methods=[...],
        allow_headers=[...],
    )
)
```

### Required Changes

Update `allow_origins` to include ALL possible frontend domains:

```python
cors=apigw.CorsOptions(
    # Allow frontend from:
    # 1. Amplify CloudFront (immediate testing)
    # 2. Custom domains (after DNS propagates)
    # 3. Localhost (local development)
    allow_origins=[
        # Amplify CloudFront distribution URL
        "https://main.d123abc.amplifyapp.com",      # prod
        "https://develop.d123abc.amplifyapp.com",   # dev
        "https://stage.d123abc.amplifyapp.com",     # stage
        
        # Custom domains (future, after DNS propagates)
        "https://app.careervp.com",                 # prod (when defined)
        "https://dev.careervp.com",                 # dev
        "https://stage.careervp.com",               # stage
        
        # Local development
        "http://localhost:3000",                    # local dev
        
        # Optional: Amplify preview deployments (if using feature branches)
        # "https://*.amplifyapp.com",  # ← WARNING: Less secure, see Security Notes
    ],
    allow_methods=[
        apigw.HttpMethod.GET,
        apigw.HttpMethod.POST,
        apigw.HttpMethod.PUT,
        apigw.HttpMethod.DELETE,
        apigw.HttpMethod.PATCH,
        apigw.HttpMethod.OPTIONS,  # ← Required for CORS preflight
    ],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Amz-Date",
        "X-Api-Key",
        "X-Amz-Security-Token",
        "X-Amz-User-Agent",
    ],
    allow_credentials=True,  # ← Required for auth tokens
    max_age=cdk.Duration.hours(1),
)
```

### Step 1: Get Amplify CloudFront URL

Before updating CDK, get your actual Amplify CloudFront URL:

1. Deploy Amplify first (see `setup.md`)
2. Go to Amplify Console → Deployments
3. Copy the URL for each branch:
   - `https://main.d123abc.amplifyapp.com` (find actual `d123abc`)
   - `https://develop.d123abc.amplifyapp.com`
   - `https://stage.d123abc.amplifyapp.com`

**Note:** The domain part (`d123abc.amplifyapp.com`) is unique to your Amplify app.

### Step 2: Update CDK

**File:** `infra/careervp/service_stack.py`

Find the CORS section and replace `allow_origins`:

```python
# BEFORE (probably looks like this):
allow_origins=["https://careervp.com", "https://localhost:3000"],

# AFTER:
allow_origins=[
    "https://main.d123abc.amplifyapp.com",
    "https://develop.d123abc.amplifyapp.com",
    "https://stage.d123abc.amplifyapp.com",
    "https://app.careervp.com",
    "https://dev.careervp.com",
    "https://stage.careervp.com",
    "http://localhost:3000",
],
```

### Step 3: Redeploy Backend

```bash
cd /Users/yitzchak/Documents/dev/careervp/infra

# Verify changes
cdk diff

# Deploy (will only update API Gateway CORS, ~2 minutes)
cdk deploy CareerVpCrudDev --require-approval never
```

**Wait for:** Stack update to complete (watch CloudFormation console or terminal output)

### Step 4: Verify CORS Headers

Test that backend returns correct CORS headers:

```bash
# Test OPTIONS request (CORS preflight)
curl -X OPTIONS \
  https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/applications \
  -H "Origin: https://main.d123abc.amplifyapp.com" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Expected response includes:
# Access-Control-Allow-Origin: https://main.d123abc.amplifyapp.com
# Access-Control-Allow-Methods: GET,POST,PUT,DELETE,PATCH,OPTIONS
# Access-Control-Allow-Credentials: true
```

---

## Security Notes

### ⚠️ Wildcard Origins (DO NOT USE)
```python
# ❌ AVOID THIS:
allow_origins=["*"],  # Too permissive

# ❌ AVOID THIS TOO:
allow_origins=["https://*.amplifyapp.com"],  # Wildcard allows anyone's Amplify app
```

**Why:** Wildcard allows any website to call your API.

### ✅ Specific Origins (REQUIRED)
```python
# ✅ DO THIS:
allow_origins=[
    "https://main.d123abc.amplifyapp.com",  # Only your domain
    "https://app.careervp.com",             # Only your domain
    "http://localhost:3000",                # Only local dev
]
```

### AllowCredentials = True
Required for:
- ✅ Sending auth tokens with requests
- ✅ Setting cookies
- ❌ Cannot be used with wildcard origins (browser blocks it)

---

## Handling Future Custom Domains

When DNS propagation completes and custom domains are active:

### Add Production Domain

Once `app.careervp.com` is defined for production:

```python
allow_origins=[
    # Amplify CloudFront (kept for fallback)
    "https://main.d123abc.amplifyapp.com",
    
    # Custom domains (primary after DNS ready)
    "https://app.careervp.com",        # ← Add when ready
    "https://dev.careervp.com",
    "https://stage.careervp.com",
    
    # Keep localhost
    "http://localhost:3000",
]
```

Then redeploy backend:
```bash
cdk deploy CareerVpCrudDev --require-approval never
```

---

## Troubleshooting

### CORS Error Still After Deployment

1. **Verify deployment completed:**
   ```bash
   aws apigateway get-rest-api --rest-api-id <API_ID> --region us-east-1
   ```

2. **Check API Gateway console:**
   - Go to API Gateway → careervp-api
   - Click any resource (e.g., `/applications`)
   - Check "CORS" tab shows your domains

3. **Test preflight again:**
   ```bash
   curl -X OPTIONS \
     https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/applications \
     -H "Origin: https://main.d123abc.amplifyapp.com" \
     -H "Access-Control-Request-Method: GET" \
     -v
   ```

### CloudFront URL Changes

If Amplify CloudFront URL changes (unlikely but possible):
1. Get new URL from Amplify Console
2. Update `allow_origins` in CDK
3. Redeploy backend

---

## Related Configuration

- **Authentication:** See `cognito-config.md` for auth token handling
- **Verification:** See `verification.md` → "API Calls"
- **Troubleshooting:** See `troubleshooting.md` → "CORS Errors"

---

**Status:** Ready to implement
**Time to deploy:** 5 minutes
**Rollback:** Revert CDK change, redeploy (2 minutes)
