# Custom Domain Setup (DNS Migration)

Configure custom domains for development, staging, and production after DNS propagation.

**Status:** This is a FUTURE step. DNS propagation can take 24-48 hours.

---

## Timeline

| Day | Phase | Action | Status |
|-----|-------|--------|--------|
| **1** | Cloudflare | Add NS records for dev/stage | ⏳ Waiting |
| **2-3** | DNS Propagation | Route53 becomes authoritative | ⏳ Waiting |
| **3-4** | SSL Validation | ACM issues certificates | ⏳ Waiting |
| **4+** | Custom Domains Live | dev/stage.careervp.com resolve | Future |
| **TBD** | Production | app.careervp.com defined | Future |

---

## Prerequisites

- [ ] Cloudflare DNS active (current provider)
- [ ] Route53 hosted zones created (dev, stage, prod)
- [ ] Amplify deployments live on CloudFront URLs
- [ ] DNS propagation 24+ hours started
- [ ] NameCheap domain ownership verified

---

## Step 1: Verify DNS Propagation (Day 3+)

### Check If Propagation Complete

```bash
# Check what Route53 NS records are
aws route53 get-hosted-zone --id /hostedzone/XXXXX --region us-east-1

# Look for:
# NameServers: [
#   "ns-123.awsdns-45.com.",
#   "ns-678.awsdns-90.com.",
#   ...
# ]
```

### Check If Cloudflare Delegation Active

```bash
# From terminal
nslookup dev.careervp.com

# Should return Route53 nameservers:
# ns-123.awsdns-45.com.
# ns-678.awsdns-90.com.
#
# If still shows Cloudflare nameservers:
# dns101.cloudflare.com
# dns102.cloudflare.com
# → Delegation not yet active, wait longer
```

### When Propagation Complete

```bash
nslookup dev.careervp.com
# Returns:
# Name: dev.careervp.com
# Address: 1.2.3.4  ← Amplify CloudFront IP
```

When this shows Amplify's IP, proceed to Step 2.

---

## Step 2: Add Custom Domain to Amplify (Dev)

### In Amplify Console

1. Go to **Amplify Console** → **careervp-frontend** app
2. Click **"Domain management"** (left sidebar)
3. Click **"Add domain"**
4. Enter: `dev.careervp.com`
5. Click **"Configure domain"**

### Amplify Validation

Amplify will:
1. Check if you own the domain (Route53 delegation)
2. Add A record in Route53
3. Create ACM SSL certificate
4. Validate certificate via DNS

**Wait for:** Status shows "Verified" (5-10 minutes)

### Monitor Progress

- Amplify Console → Domain management
- Click `dev.careervp.com`
- Watch status: "In progress" → "Verified"
- When "Verified", domain is live

### Test Domain

```bash
curl https://dev.careervp.com/

# Should return HTML (same as CloudFront URL)
# OR
# Open in browser: https://dev.careervp.com
# Should load dashboard
```

---

## Step 3: Add Stage Domain

Repeat Step 2 for `stage.careervp.com`:

1. Amplify Console → Domain management → Add domain
2. Enter: `stage.careervp.com`
3. Configure domain
4. Wait for "Verified"
5. Test domain

---

## Step 4: Define Production Domain

**Timeline:** When ready for production launch

### Option A: Use app.careervp.com (Recommended)

1. **Verify domain registered:**
   - NameCheap → My Domains → careervp.com
   - Check if `app` subdomain can be configured

2. **Create Route53 hosted zone for app:**
   ```bash
   aws route53 create-hosted-zone \
     --name app.careervp.com \
     --region us-east-1 \
     --caller-reference $(date +%s)
   
   # Get the nameservers output
   ```

3. **Add NS records to Cloudflare:**
   - Cloudflare DNS → Records
   - Type: NS
   - Name: app
   - Nameserver: (first Route53 NS from above)
   - Add another record for each additional NS record
   - Save

4. **Wait for propagation:**
   ```bash
   nslookup app.careervp.com
   # Wait until returns Route53 nameserver
   ```

5. **Add to Amplify:**
   - Same as Step 2, but use `app.careervp.com`

### Option B: Use careervp.com (Apex Domain)

**Note:** Root domain is more complex, requires careful DNS setup

1. Create Route53 hosted zone for `careervp.com`
2. Update NameCheap to use Route53 nameservers
3. Add Amplify with apex domain
4. Set up HTTPS redirection

**Recommendation:** Use `app.careervp.com` instead (simpler, safer)

---

## Step 5: Update Backend CORS (If Needed)

Once custom domains are live, backend CORS might still reference old CloudFront URLs.

### Check Current CORS

```bash
curl -X OPTIONS https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/applications \
  -H "Origin: https://dev.careervp.com" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Should show:
# Access-Control-Allow-Origin: https://dev.careervp.com
```

### If CORS Missing

1. Edit `infra/careervp/service_stack.py`
2. Verify `allow_origins` includes:
   ```python
   allow_origins=[
       "https://main.d123abc.amplifyapp.com",  # Keep for fallback
       "https://dev.careervp.com",             # Add custom domain
       "https://stage.careervp.com",
       "https://app.careervp.com",
       ...
   ]
   ```
3. Redeploy backend:
   ```bash
   cd infra
   cdk deploy CareerVpCrudDev --require-approval never
   ```

---

## Step 6: Update Cognito Callbacks (If Needed)

Once custom domains are live, verify Cognito already has callback URLs.

### Check Cognito Callbacks

1. AWS Cognito → User Pools → careervp-pool → App Clients
2. Check "Allowed callback URLs"
3. Should already include:
   ```
   https://dev.careervp.com/callback
   https://stage.careervp.com/callback
   https://app.careervp.com/callback
   ```

**If missing:** Add them (see `cognito-config.md`)

---

## Step 7: Verify Custom Domains

### Full Test on Each Domain

1. **Open domain in browser:**
   ```
   https://dev.careervp.com
   ```

2. **Verify page loads:**
   - Dashboard visible
   - No errors in DevTools → Console
   - HTTPS padlock shows in address bar

3. **Test authentication:**
   - Click Login
   - Should redirect to Cognito with correct callback URL
   - Login succeeds
   - Redirected back to domain

4. **Test API calls:**
   - DevTools → Network tab
   - Verify API calls to backend succeed
   - Check for CORS errors (should be none)

5. **Test logout:**
   - Click Logout
   - Should redirect cleanly
   - Token removed

**Repeat for:** dev, stage, and prod domains

---

## Step 8: Remove CloudFront URLs from Amplify (Optional)

Once custom domains are stable, you can remove old CloudFront URLs to simplify.

### Before Removing

- [ ] All custom domains working
- [ ] No traffic on old URLs (analytics)
- [ ] All certificates valid
- [ ] 24+ hours tested on custom domains

### To Remove

1. Amplify Console → Domain management
2. Click old CloudFront domain (e.g., `main.d123abc.amplifyapp.com`)
3. Click **"Disconnect domain"**
4. CloudFront URL stops working (expected)

**Note:** Can be re-enabled if needed (no deletion)

---

## Monitoring Post-Migration

### Week 1

- [ ] Check SSL certificate expiration (Amplify dashboard)
- [ ] Monitor error rates (should be same as before)
- [ ] Check API latency (should improve slightly from Route53 routing)
- [ ] Verify no 404s on new domains

### Ongoing

- [ ] Renew SSL certificates (Amplify handles auto-renewal)
- [ ] Monitor DNS propagation in different regions
- [ ] Check domain registration status (NameCheap)
- [ ] Review access logs for unusual traffic

---

## Troubleshooting DNS Issues

### Domain Still Shows 404

1. **Check DNS propagation:**
   ```bash
   nslookup dev.careervp.com
   # Should return Amplify CloudFront IP, not error
   ```

2. **If still Cloudflare:**
   - Cloudflare delegated NS records not saved
   - Verify in Cloudflare DNS → Records
   - Check all 4 Route53 NS records added

3. **Wait longer:**
   - DNS propagation can take up to 48 hours
   - Try again in 30 minutes

### Domain Resolves But Shows 403 Forbidden

1. **Check Amplify domain status:**
   - Amplify Console → Domain management
   - Status should be "Verified" (not "In progress")
   - If "In progress", wait for verification

2. **Check Route53 records:**
   ```bash
   aws route53 list-resource-record-sets \
     --hosted-zone-id /hostedzone/XXXXX \
     --region us-east-1
   
   # Should show A record pointing to Amplify CloudFront
   ```

3. **Invalidate CloudFront cache:**
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id <ID> \
     --paths "/*"
   ```

### SSL Certificate Shows as Pending

1. **Check ACM certificate status:**
   ```bash
   aws acm list-certificates --region us-east-1
   # Look for dev.careervp.com
   ```

2. **Validation via DNS:**
   - ACM creates DNS record in Route53
   - Must validate within 72 hours
   - Amplify handles this automatically

3. **If stuck:**
   - Wait 30 more minutes (DNS propagation)
   - Or manually validate in ACM console

---

## Rollback Plan

If custom domain causes issues:

### Immediate Rollback

1. **Update Cognito:**
   - Revert callback URLs to only CloudFront
   - Remove custom domain callbacks

2. **Update CORS:**
   - Revert backend CORS to only CloudFront domain
   - Redeploy CDK

3. **Users access via CloudFront:**
   - URL changes back to: `https://main.d123abc.amplifyapp.com`
   - Bookmark changes required

### Full Revert

If DNS issues:

1. Amplify Console → Domain management
2. Click custom domain → Disconnect
3. Users go back to CloudFront URLs

---

## Future: Subdomain Delegation

When growing, can delegate subdomains to different services:

```
careervp.com (parent)
├── app.careervp.com → Amplify (frontend)
├── api.careervp.com → Lambda (backend)
├── admin.careervp.com → Future admin panel
└── blog.careervp.com → Future blog
```

Each subdomain can have its own Route53 hosted zone and NS delegation.

---

**Status:** Future step, placeholder for DNS propagation
**Timeline:** Days 3-7 after Cloudflare NS delegation started
**Blocker:** DNS propagation (not under your control)
**Rollback:** Easy (Amplify disconnects domain in 1 click)
