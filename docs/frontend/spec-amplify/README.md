# AWS Amplify Frontend Deployment Specification

## Overview

Deploy CareerVP Next.js frontend to AWS Amplify with full backend API integration and Cognito authentication. This spec covers immediate testing on Amplify CloudFront distribution and future custom domain setup.

## Architecture Decision

| Component | Platform | Status |
|-----------|----------|--------|
| Frontend | AWS Amplify (Next.js) | Implementing |
| Backend API | AWS Lambda + API Gateway | Deployed ✅ |
| Auth | Amazon Cognito | Configured, callbacks pending |
| CDN | CloudFront (via Amplify) | Automatic |
| DNS | Route53 + Cloudflare | In transition |

## DNS Status & Timeline

### Current State (Day 1-7)
- `dev.careervp.com` → Waiting Route53 NS propagation via Cloudflare
- `stage.careervp.com` → Waiting Route53 NS propagation via Cloudflare
- `app.careervp.com` → Not yet defined
- **Testing method:** Use Amplify CloudFront distribution URL directly (e.g., `https://d123abc.amplifyapp.com`)

### Future State (Day 7+)
- `dev.careervp.com` → Points to Amplify dev deployment
- `stage.careervp.com` → Points to Amplify stage deployment
- `app.careervp.com` → Points to Amplify prod deployment

## Prerequisites

- [ ] AWS account (us-east-1) with Amplify permissions
- [ ] GitHub repo connected via OAuth
- [ ] Backend API deployed and accessible
  - Endpoint: `https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod`
  - Status: Check with `curl https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/health`
- [ ] Cognito User Pool configured
  - Pool ID: `us-east-1_WiHMRqLpe`
  - Client ID: `7blipbarsisbctqh6hlsj46sqa`
- [ ] NameCheap domain access (for future prod setup)

## Success Criteria

### Phase 1: Amplify Deployment (Day 1)
- [ ] Frontend builds successfully on Amplify
- [ ] CloudFront URL is publicly accessible
- [ ] Dashboard loads without errors
- [ ] Network requests show no 403/CORS errors

### Phase 2: Backend Integration (Day 1)
- [ ] Backend CORS headers allow Amplify CloudFront domain
- [ ] API calls from frontend succeed
- [ ] Application list loads from backend
- [ ] Network tab shows 200 responses from backend

### Phase 3: Authentication (Day 1)
- [ ] Cognito callbacks include Amplify URL
- [ ] Login flow works end-to-end
- [ ] Access tokens are received and stored
- [ ] Protected routes require authentication

### Phase 4: Custom Domains (Days 7+)
- [ ] dev.careervp.com resolves to Amplify deployment
- [ ] stage.careervp.com resolves to Amplify deployment
- [ ] app.careervp.com defined and routable (prod)
- [ ] SSL certificates valid for all domains

## Implementation Timeline

| Phase | Duration | Blockers |
|-------|----------|----------|
| Amplify setup | 15 min | None |
| Backend CORS fix | 20 min | CDK redeploy |
| Cognito config | 10 min | AWS Cognito console access |
| Verification | 15 min | Backend must respond |
| Total | ~60 min | Backend deployed |

## Key Decisions

### Decision 1: Amplify for Frontend
**Why:** Managed service, no cold starts (unlike Lambda), automatic CloudFront CDN, built-in CI/CD
**Alternative rejected:** Lambda Docker (cold starts, higher ops complexity)

### Decision 2: CloudFront URL for Immediate Testing
**Why:** DNS propagation takes 24-48 hours; Amplify URL works immediately
**DNS domains:** Added after propagation, no codebase changes needed (env vars handle routing)

### Decision 3: CORS for Both CloudFront & Custom Domains
**Why:** Supports testing on Amplify URL AND custom domains once ready
**Implementation:** Backend allows origins list in CDK

### Decision 4: Cognito Callbacks Include All Domains
**Why:** Single Cognito pool supports all environments (dev/stage/prod)
**Implementation:** Add callback URLs for each domain to User Pool App Client

## File Structure

```
docs/frontend/spec-amplify/
├── README.md                    # This file
├── setup.md                     # Step-by-step Amplify deployment
├── backend-cors.md             # Backend API Gateway CORS config
├── cognito-config.md           # Cognito callback URL setup
├── environment.md              # Environment variables per branch
├── deployment.md               # Automated deployment workflow
├── verification.md             # Testing checklist
├── security-checklist.md       # Security & compliance review
├── troubleshooting.md          # Common issues & fixes
└── dns-migration.md            # Custom domain setup (future)
```

## Quick Start

1. **Remove static export** → `setup.md` Step 1
2. **Create Amplify app** → `setup.md` Step 2
3. **Fix backend CORS** → `backend-cors.md`
4. **Update Cognito** → `cognito-config.md`
5. **Deploy** → `setup.md` Step 3
6. **Test** → `verification.md`

## Rollback Plan

If deployment fails:

| Issue | Rollback | Time |
|-------|----------|------|
| Build fails | Revert Git commit | 2 min |
| API calls fail | Restore previous CORS config | 10 min |
| Auth fails | Restore previous Cognito callbacks | 5 min |
| Amplify down | DNS points to S3 backup (if available) | 5 min |

## Cost Estimate

| Service | Monthly Cost | Notes |
|---------|--------------|-------|
| Amplify | $0-15 | Free tier includes 100 build min/month |
| CloudFront | Included | Amplify manages |
| Data transfer | $0-5 | Dev/stage negligible |
| **Total** | **$0-20** | Dev/stage free tier likely covers |

## Security Summary

- ✅ CORS restricted to known Amplify domain
- ✅ Backend CORS enforced (not `*` allow-all)
- ✅ Cognito callbacks match registered domains
- ✅ Environment variables not committed
- ✅ Build secrets stored in AWS Secrets Manager
- ⚠️ HTTPS enforced (Amplify default)
- ⚠️ CloudFront caching headers configured (see `security-checklist.md`)

## Support & Troubleshooting

See `troubleshooting.md` for:
- Build failures
- CORS errors
- Auth flow issues
- DNS propagation delays
- Performance optimization

---

**Status:** Draft spec — Ready for implementation
**Last Updated:** 2026-04-25
**Owner:** Yitzchak Meirovich
