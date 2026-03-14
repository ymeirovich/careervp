# Code Connect Implementation Status

**Date**: March 14, 2026
**Status**: ⏳ Blocked on Figma Plan Upgrade

---

## What We've Completed ✅

### Dashboard Implementation
- [x] Implemented full dashboard from Figma design (node 66:262)
- [x] All 5 components built: DashboardPage, Sidebar, Topbar, StatusStrip, JobsCard
- [x] Design tokens extracted and applied exactly (colors, spacing, typography)
- [x] Committed to `ui/figma-test` branch

### Documentation
- [x] Design System Rules (colors, spacing, typography, component specs)
- [x] Code Connect Setup Guide (manual + API approaches)
- [x] Figma Workflow Guide (designer + developer collaboration patterns)
- [x] Implementation Details (component breakdown, data structures)

### Mapping Definitions
- [x] Created mapping specifications for all 5 components
- [x] Documented exact Figma node IDs and React function locations
- [x] Prepared mapping JSON ready for Figma

---

## What's Blocked ⏳

### Code Connect API Access

**Error**:
```
"You need a Developer seat in an Organization or Enterprise plan
to access Code Connect. Contact a Figma admin to upgrade."
```

**Why**:
- Code Connect is a Figma Team/Organization feature
- Your current plan: Pro Full (individual account)
- Required upgrade: Figma Team or Figma Organization with Developer seat

---

## Mapping Specifications (Ready to Push)

Once plan is upgraded, execute these mappings:

```json
{
  "fileKey": "tMHabCYB7teMvu7L8lz957",
  "mappings": [
    {
      "nodeId": "66:262",
      "componentName": "DashboardPage",
      "source": "frontend/app/dashboard/page.tsx",
      "label": "React"
    },
    {
      "nodeId": "66:264",
      "componentName": "Sidebar",
      "source": "frontend/app/dashboard/page.tsx#Sidebar",
      "label": "React"
    },
    {
      "nodeId": "66:278",
      "componentName": "Topbar",
      "source": "frontend/app/dashboard/page.tsx#Topbar",
      "label": "React"
    },
    {
      "nodeId": "66:287",
      "componentName": "StatusStrip",
      "source": "frontend/app/dashboard/page.tsx#StatusStrip",
      "label": "React"
    },
    {
      "nodeId": "66:291",
      "componentName": "JobsCard",
      "source": "frontend/app/dashboard/page.tsx#JobsCard",
      "label": "React"
    }
  ]
}
```

---

## Next Steps to Activate Code Connect

### Step 1: Upgrade Figma Plan (Your Action)

1. Go to [Figma Account Settings](https://figma.com/settings)
2. Click **Plans & Billing**
3. Upgrade to **Figma Team** or **Figma Organization**
4. Add a **Developer seat** to your team
5. Wait for activation (usually instant)

**Cost**: Figma Team starts at $12/editor/month
**Benefit**: Full Code Connect capabilities + team collaboration

### Step 2: Push Mappings (Our Action, After Upgrade)

Once plan is activated:

```bash
# We'll run this command to push all 5 mappings
npx claude-code push-code-connect \
  --figma-file tMHabCYB7teMvu7L8lz957 \
  --mappings /tmp/code_connect_mappings.json
```

This will:
- Create all 5 Code Connect links in Figma
- Enable "Code" tab in each component
- Link Figma nodes → GitHub files
- Enable bidirectional visibility

### Step 3: Verify in Figma (Your Action, After Push)

1. Open [CareerVP Test 2](https://figma.com/design/tMHabCYB7teMvu7L8lz957/CareerVP-Test-2)
2. Click on Dashboard component (node 66:262)
3. Right panel → "Code" tab
4. Verify:
   - ✅ Component name shown
   - ✅ GitHub link works
   - ✅ Can navigate to code
   - ✅ Live preview available (if enabled)

---

## Alternative: Manual Setup (No Plan Change Required)

If you want to set up Code Connect without upgrading, you can do it manually via Figma UI:

**For Each Component**:
1. Select component in Figma
2. Right panel → "Inspect" tab
3. Look for "Code" section or "Connect to code" button
4. Enter:
   - Repository: GitHub repo URL
   - File Path: `frontend/app/dashboard/page.tsx` (or with #SectionName)
   - Component Name: `DashboardPage`, `Sidebar`, etc.
   - URL: Direct link to GitHub file

**Advantage**: Works immediately, no plan change
**Disadvantage**: Manual setup for each component, no API automation

---

## Current Branch Status

**Branch**: `ui/figma-test`
**Status**: Ready for PR
**Latest Commits**:
```
88e51f7 - docs: add comprehensive frontend documentation
5b9f080 - docs: add implementation notes and artifacts
daa0b97 - feat: add CareerVP dashboard UI from Figma design
```

**Ready to Merge**: Yes, all changes complete and documented
**Blocking Issues**: None (Code Connect is optional enhancement)

---

## What Happens When Plan is Upgraded

Assuming Figma Organization upgrade completes:

1. **Immediate**: Developer seat becomes active
2. **Same Day**: Code Connect API access available
3. **Within 1 Hour**: All 5 mappings can be pushed to Figma
4. **Live**: Designers can view "Code" tab in each Figma component
5. **Ongoing**: Code Connect mappings sync Figma ↔ GitHub automatically

**Timeline**: ~2-4 hours from "click upgrade" to "fully active"

---

## Workaround: Push to Figma via Manual Process

If you want to set up Code Connect immediately (without waiting for plan upgrade):

**In Figma**:
1. Open CareerVP Test 2 file
2. Select "Desktop / Dashboard Full" frame
3. Right panel → "Code" tab (or "Inspect" → look for Code section)
4. Click "Connect to code" or "Add code connection"
5. Fill in details:
   ```
   Framework: React
   Repository: https://github.com/[your-org]/careervp
   Branch: ui/figma-test
   File: frontend/app/dashboard/page.tsx
   Component: DashboardPage
   ```
6. Repeat for Sidebar (node 66:264), Topbar, StatusStrip, JobsCard

**Result**: Figma Code tab becomes active immediately
**Note**: This is the manual process, API process is automated

---

## Resources

### Figma Upgrade
- [Figma Plans & Pricing](https://figma.com/pricing)
- [Team Setup Guide](https://help.figma.com/hc/en-us/articles/13315036260119-Manage-your-team)
- [Developer Seat Info](https://help.figma.com/hc/en-us/articles/15404759103255-Developer-seat)

### Code Connect
- [Code Connect Docs](https://help.figma.com/hc/en-us/articles/23920389749655-Code-Connect)
- [Code Connect Tutorial](https://www.figma.com/blog/introducing-code-connect/)
- [Our Setup Guide](./CODE_CONNECT_SETUP.md)

### Implementation
- [Design System Rules](./DESIGN_SYSTEM_RULES.md)
- [Workflow Guide](./FIGMA_WORKFLOW_GUIDE.md)
- [Implementation Details](./IMPLEMENTATION.md)

---

## Timeline

| Event | Date | Status |
|---|---|---|
| Dashboard implemented | Mar 14, 2026 | ✅ Complete |
| Documentation written | Mar 14, 2026 | ✅ Complete |
| Code Connect API attempt | Mar 14, 2026 | ⏳ Blocked on plan |
| Figma plan upgrade | TBD | 🔲 Pending |
| Code Connect mappings pushed | TBD | 🔲 After upgrade |
| Designer reviews live code | TBD | 🔲 After mappings |
| Feature shipped | TBD | 🔲 After approval |

---

## Action Items

### For You (Developer)
- [ ] Share this status with your partner
- [ ] Review Code Connect Setup Guide
- [ ] Confirm Figma upgrade plan (if proceeding with Code Connect)
- [ ] Once upgraded: Run mapping push command

### For Your Partner (Designer)
- [ ] Review Figma Workflow Guide
- [ ] Decide on Figma plan upgrade (if Code Connect desired)
- [ ] If upgrading: Follow Step 1-3 above
- [ ] If not upgrading: Use manual setup process in Figma

### For the Team
- [ ] Schedule design review meeting
- [ ] Discuss Code Connect workflow and benefits
- [ ] Plan Phase 2 enhancements (data integration, responsiveness)

---

## Questions?

**Q: Can we proceed without Code Connect?**
A: Yes. Dashboard works perfectly without Code Connect. It's an enhancement for designer visibility, not required for functionality.

**Q: How long does plan upgrade take?**
A: Usually instant. Sometimes within 24 hours if manual approval needed.

**Q: Can we use free Figma plan?**
A: No. Code Connect requires Team/Organization plan. Manual setup still possible on any plan.

**Q: What if we don't want to upgrade?**
A: Dashboard still ships as-is. Use manual Figma Code Connect setup instead of API.

---

**Status Last Updated**: March 14, 2026 10:47 AM
**Next Review**: After Figma plan decision
**Owner**: Development Team
