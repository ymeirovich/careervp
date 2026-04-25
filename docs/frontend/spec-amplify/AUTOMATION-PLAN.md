# Automation Plan: Manual + Automated Steps

Clear sequencing of which steps you do, which are automated, and when to coordinate.

---

## Overview

| Phase | Owner | Time | Steps |
|-------|-------|------|-------|
| **Phase 1: Prepare Code** | Automation | 5 min | Remove static export, commit |
| **Phase 2: Create Amplify** | YOU | 10 min | Create app, get CloudFront URL |
| **Phase 3: Configure Backend** | Automation (you provide URL) | 15 min | Update CORS, deploy CDK |
| **Phase 4: Configure Cognito** | YOU | 5 min | Update callbacks, save |
| **Phase 5: Verify** | YOU (+ automated tests) | 20 min | Browser testing |
| | | **~55 min** | |

---

## Phase 1: Prepare Code (AUTOMATED)

**What:** Remove static export, commit to Git

**Who:** Automation (Sonnet agent)

**What will be automated:**
1. Edit `src/frontend/next.config.js` → Remove `output: 'export'` line
2. Test build locally to verify it works
3. Commit change: `"feat(frontend): prepare for Amplify deployment"`
4. Push to current branch

**Code change (for reference):**
```javascript
// BEFORE:
module.exports = {
  output: 'export',  // ← REMOVE THIS LINE
  env: { ... }
}

// AFTER:
module.exports = {
  env: { ... }
}
```

**Status:** ⏳ Will be automated when you approve

---

## Phase 2: Create Amplify App (YOU)

**What:** Create Amplify app in AWS console

**Who:** YOU (manual)

**Steps:**
1. Open AWS Amplify Console
2. Click "Create app" → "Host web app" → GitHub
3. Authorize AWS OAuth
4. Select `careervp` repo + `main` branch
5. Accept build settings
6. Click "Save and deploy"
7. **Wait** for deployment (3-5 min)
8. **COPY** the CloudFront URL from Deployments tab

**CloudFront URL example:**
```
https://main.d123abc.amplifyapp.com
```

**Important:** You MUST get this URL before proceeding to Phase 3

**Instructions:** See `MANUAL-ONLY.md` → STEP 1 & STEP 2

---

## ⏸️ CHECKPOINT: Provide CloudFront URL

**Before continuing, you must:**
1. Provide me the CloudFront URL from Phase 2
2. Example message:
   ```
   Phase 2 complete. CloudFront URL is: https://main.d123abc.amplifyapp.com
   
   Ready for Phase 3.
   ```

**What happens next:** I'll use your CloudFront URL in Phase 3 automation

---

## Phase 3: Configure Backend (AUTOMATED)

**What:** Update CORS in CDK, deploy to AWS

**Who:** Automation (Sonnet agent)

**What will be automated:**
1. Get your CloudFront URL from you
2. Edit `infra/careervp/service_stack.py`
   - Add your CloudFront URL to `allow_origins`
   - Add all future domain URLs too
3. Verify syntax is correct
4. Commit change
5. Run `cdk deploy CareerVpCrudDev`
6. **Wait** for stack update (~2-3 min)
7. Verify deployment succeeded

**Code change (for reference):**
```python
# BEFORE:
allow_origins=["https://careervp.com", ...],

# AFTER:
allow_origins=[
    "https://main.d123abc.amplifyapp.com",  # ← Added
    "https://develop.d123abc.amplifyapp.com",
    "https://stage.d123abc.amplifyapp.com",
    "https://app.careervp.com",
    "https://dev.careervp.com",
    "https://stage.careervp.com",
    "http://localhost:3000",
],
```

**Status:** ⏳ Will be automated after you provide CloudFront URL

**How to trigger:**
```
I got the CloudFront URL. Ready to automate Phase 3.
```

---

## Phase 4: Configure Cognito (YOU)

**What:** Update callback URLs in Cognito

**Who:** YOU (manual)

**Steps:**
1. Open AWS Cognito → User Pools → careervp-pool
2. App Clients → 7blipbarsisbctqh6hlsj46sqa
3. Update "Allowed callback URLs" with all 7 (see MANUAL-ONLY.md)
4. Update "Allowed sign-out URLs" with all 7
5. Update "Allowed origins" with all 7
6. **Click Save**

**URLs to add (use your CloudFront subdomain):**
```
https://main.d123abc.amplifyapp.com/callback
https://develop.d123abc.amplifyapp.com/callback
https://stage.d123abc.amplifyapp.com/callback
https://app.careervp.com/callback
https://dev.careervp.com/callback
https://stage.careervp.com/callback
http://localhost:3000/callback

(and similar for sign-out URLs without /callback)
```

**Instructions:** See `MANUAL-ONLY.md` → STEP 4

**When to do:** After you see Phase 3 is complete

---

## Phase 5: Verify Deployment (YOU + AUTOMATED TESTS)

**What:** Test that everything works end-to-end

**Who:** YOU (manual browser testing) + Automation (automated tests)

**What you'll do manually:**
1. Open CloudFront URL in browser
2. Verify dashboard loads
3. Check application list displays
4. Test login flow (redirect to Cognito → login → back to app)
5. Verify auth token stored
6. Confirm API calls include auth token
7. Test logout

**Detailed steps:** See `MANUAL-ONLY.md` → STEP 5

**Automated tests:**
- CORS header verification
- API health check
- Frontend bundle size check
- Build log analysis

---

## Timeline Visualization

```
Phase 1: Prepare Code
├─ Remove static export
├─ Commit to Git
└─ Time: 5 min [AUTOMATED]

Phase 2: Create Amplify App
├─ Create Amplify app
├─ Authorize GitHub
├─ Wait for deployment
├─ Copy CloudFront URL
└─ Time: 10 min [YOU]

⏸️ CHECKPOINT: Give me CloudFront URL

Phase 3: Configure Backend
├─ Update CORS in CDK
├─ Deploy CDK stack
├─ Verify deployment
└─ Time: 15 min [AUTOMATED]

Phase 4: Configure Cognito
├─ Update callback URLs
├─ Update sign-out URLs
├─ Update allowed origins
├─ Save changes
└─ Time: 5 min [YOU]

Phase 5: Verify Deployment
├─ Test dashboard loads
├─ Test API calls
├─ Test login flow
├─ Test logout
├─ Run automated tests
└─ Time: 20 min [YOU + AUTOMATED TESTS]

SUCCESS ✅
```

---

## Step-by-Step Instructions

### Your Action: Start Phase 1

Tell me you're ready, and I'll automate Phase 1:

```
Ready to start. Execute Phase 1 automation.
```

I'll respond with:
```
✅ Phase 1 complete:
- next.config.js updated (removed output: 'export')
- Changes committed to git
- Build tested locally

Next: You do Phase 2 (Create Amplify App)
See: MANUAL-ONLY.md → STEP 1
```

### Your Action: Complete Phase 2

Follow instructions in `MANUAL-ONLY.md` → STEP 1 & STEP 2

When done, tell me:
```
Phase 2 complete. CloudFront URL is: https://main.d123abc.amplifyapp.com
```

### Automation: Execute Phase 3

I'll respond with:
```
Automating Phase 3...
✅ Phase 3 complete:
- CORS updated in CDK
- Backend deployed
- CloudFront domain added to allow_origins

Next: You do Phase 4 (Configure Cognito)
See: MANUAL-ONLY.md → STEP 4
```

### Your Action: Complete Phase 4

Follow instructions in `MANUAL-ONLY.md` → STEP 4

When done, tell me:
```
Phase 4 complete. Cognito callbacks saved.
```

### Your Action: Complete Phase 5

Follow instructions in `MANUAL-ONLY.md` → STEP 5

When done, tell me:
```
Phase 5 complete. All tests passed ✅
```

---

## Error Recovery

If any step fails:

1. **Phase 1 fails:** Automation retries, or I debug the issue
2. **Phase 2 fails:** Check AWS account permissions, try again
3. **Phase 3 fails:** Check CloudFront URL format, automation retries
4. **Phase 4 fails:** Check Cognito console, re-save changes
5. **Phase 5 fails:** See `troubleshooting.md` in spec-amplify folder

---

## After Phase 5: Next Steps

Once all phases complete:

1. ✅ Website loads via CloudFront
2. ✅ API calls work
3. ✅ Auth flow works

What's left:
- **DNS propagation** (24-48 hours) → dev.careervp.com goes live
- **Production setup** (define app.careervp.com)
- **Security review** (before prod launch)

See other spec files for those phases.

---

## Quick Reference: File Locations

| Phase | Manual | Automated |
|-------|--------|-----------|
| 1 | — | next.config.js |
| 2 | MANUAL-ONLY.md STEP 1-2 | — |
| 3 | — | service_stack.py |
| 4 | MANUAL-ONLY.md STEP 4 | — |
| 5 | MANUAL-ONLY.md STEP 5 | verification.md |

---

## Ready to Begin?

Say this to start:

```
Ready to start Amplify deployment. Execute Phase 1 automation.
```

Then I'll:
1. Remove static export from next.config.js
2. Test the build
3. Commit to Git
4. Tell you it's done

After that, you follow MANUAL-ONLY.md for Phases 2-5.

---

**Status:** Ready for execution
**Total time:** ~55 minutes
**Automated:** ~35 minutes (Phases 1, 3, 5 testing)
**Manual:** ~20 minutes (Phases 2, 4, 5 testing)
