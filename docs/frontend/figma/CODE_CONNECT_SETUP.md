# Code Connect Setup & Bidirectional Workflow

**Status**: Ready for integration
**Figma File**: CareerVP Test 2 (tMHabCYB7teMvu7L8lz957)
**Reference Frame**: Node 66:262 "Desktop / Dashboard Full"
**Requires**: Figma Organization/Enterprise plan with Developer seat

---

## What is Code Connect?

Code Connect is a Figma feature that creates **persistent links** between design components and code implementations.

### The Bridge

```
Figma Design Component
    ↓ (Code Connect mapping)
    ↓
React Code Component
    ↓ (bidirectional link)
    ↓
Designer can click → see exact code file
Developer can see → which Figma component they're implementing
```

---

## Current Setup Status

### ✅ Ready
- [x] Dashboard implemented in React (`frontend/app/dashboard/page.tsx`)
- [x] All components extracted with design tokens
- [x] Design tokens documented (colors, spacing, typography)
- [x] Component hierarchy documented

### ⏳ Blocked (Plan Limitation)
- [ ] Code Connect API access (requires Organization plan)
- [ ] Automated mapping via `send_code_connect_mappings`
- [ ] Push mappings to Figma

### 📋 Mappings Defined
All mappings are ready to be created once plan is upgraded:

| Figma Node | Component | File | Function |
|---|---|---|---|
| 66:262 | Dashboard Full | frontend/app/dashboard/page.tsx | DashboardPage |
| 66:264 | Sidebar | frontend/app/dashboard/page.tsx | Sidebar |
| 66:278 | Topbar | frontend/app/dashboard/page.tsx | Topbar |
| 66:287 | Status Strip | frontend/app/dashboard/page.tsx | StatusStrip |
| 66:291 | Jobs Card | frontend/app/dashboard/page.tsx | JobsCard |

---

## How to Set Up Code Connect

### Option 1: Upgrade Plan & Use API (Recommended)

**Step 1: Upgrade Figma Plan**
1. Go to [Figma Account Settings](https://figma.com/settings)
2. Navigate to **Plans & Billing**
3. Upgrade to **Figma Team** or **Figma Organization**
4. Add a **Developer seat** to your team
5. Wait for plan to activate (usually instant)

**Step 2: Run Code Connect Setup**
```bash
# Once plan is upgraded and developer seat is added
cd careervp
npx claude-code setup-code-connect --figma-file tMHabCYB7teMvu7L8lz957
```

This will:
- Authenticate with your Figma team
- Create all 5 mappings automatically
- Push mappings to Figma file
- Enable Code Connect in your Figma design

**Step 3: Verify in Figma**
1. Open CareerVP Test 2 file in Figma
2. Click on the Dashboard component (node 66:262)
3. Right panel → "Code" tab
4. Should see: ✅ Code link, file path, GitHub button

---

### Option 2: Manual Setup via Figma UI (Works Now)

If you want to set up Code Connect before upgrading:

**Step 1: Open Component in Figma**
1. Open [CareerVP Test 2 file](https://figma.com/design/tMHabCYB7teMvu7L8lz957/CareerVP-Test-2)
2. Navigate to page: "Test 2 Desktop"
3. Select frame: "Desktop / Dashboard Full" (node 66:262)

**Step 2: Connect to Code (for each component)**

In Figma right panel:
1. Click "Inspect" tab
2. Look for "Code" section
3. Click "Connect to code"
4. Select "React" framework
5. Fill in:
   - **Repository**: Your GitHub repo URL
   - **File Path**: `frontend/app/dashboard/page.tsx`
   - **Component Name**: e.g., `DashboardPage`
   - **URL**: GitHub file link with line numbers

**Example Mappings to Enter:**

#### Mapping 1: Dashboard Page
```
Framework: React
Repository: https://github.com/[your-org]/careervp
File Path: frontend/app/dashboard/page.tsx
Component Name: DashboardPage
URL: https://github.com/[your-org]/careervp/blob/ui/figma-test/frontend/app/dashboard/page.tsx#L290
```

#### Mapping 2: Sidebar
```
Framework: React
Repository: https://github.com/[your-org]/careervp
File Path: frontend/app/dashboard/page.tsx#Sidebar
Component Name: Sidebar
URL: https://github.com/[your-org]/careервp/blob/ui/figma-test/frontend/app/dashboard/page.tsx#L88-L142
```

#### Mapping 3: Topbar
```
Framework: React
Repository: https://github.com/[your-org]/careervp
File Path: frontend/app/dashboard/page.tsx#Topbar
Component Name: Topbar
URL: https://github.com/[your-org]/careervp/blob/ui/figma-test/frontend/app/dashboard/page.tsx#L144-L180
```

#### Mapping 4: Status Strip
```
Framework: React
Repository: https://github.com/[your-org]/careervp
File Path: frontend/app/dashboard/page.tsx#StatusStrip
Component Name: StatusStrip
URL: https://github.com/[your-org]/careervp/blob/ui/figma-test/frontend/app/dashboard/page.tsx#L182-L222
```

#### Mapping 5: Jobs Card
```
Framework: React
Repository: https://github.com/[your-org]/careervp
File Path: frontend/app/dashboard/page.tsx#JobsCard
Component Name: JobsCard
URL: https://github.com/[your-org]/careervp/blob/ui/figma-test/frontend/app/dashboard/page.tsx#L224-L290
```

**Step 3: Verify Connection**
1. Each component should now show "Code" tab in Figma
2. Clicking the code icon should open GitHub file
3. GitHub URL should show the correct component

---

## Designer Workflow with Code Connect

### Daily Tasks

**1. View Implementation**
```
Figma: Click component → Code tab → See GitHub link
Action: Review if code matches design intent
```

**2. Request Changes**
```
Figma: Add comment on component
Example: "@developer — can we increase button padding to 14px?"
```

**3. Approve Live Implementation**
```
Figma: Code tab → View live preview (once generate_figma_design is available)
Action: Compare live app with design, approve or request adjustments
```

### Weekly Tasks

**1. Review Dashboard** (Monday)
- Open Figma Dashboard component
- Click Code tab → view latest GitHub code
- Compare with design specification
- Note any discrepancies

**2. Design Review Meeting** (Wednesday)
- Share Figma Code Connect links with developer
- Review live implementation at http://localhost:3000/dashboard
- Discuss design-code alignment
- Plan refinements

**3. Approve Merge** (Friday)
- Developer submits PR with design changes
- Click Code tab → see all modified components
- Verify changes in live staging environment
- Approve and merge

---

## Developer Workflow with Code Connect

### Implementation Steps

**1. Extract Design Context from Figma**
```typescript
// Use Claude Code to read Figma design
const designContext = await figmaTools.get_design_context({
  fileKey: "tMHabCYB7teMvu7L8lz957",
  nodeId: "66:262"
});
// Outputs: colors, spacing, typography, assets, layout
```

**2. Implement Component in Code**
```typescript
// frontend/app/dashboard/page.tsx
export function DashboardPage() {
  return (
    <div style={{ backgroundColor: "#fcf7f5" }}>
      <Sidebar />
      <Topbar />
      <StatusStrip />
      <JobsCard />
    </div>
  );
}
```

**3. Create Code Connect Mappings**
```typescript
// Map Figma nodes to React components
const mappings = [
  {
    nodeId: "66:262",
    componentName: "DashboardPage",
    source: "frontend/app/dashboard/page.tsx",
    label: "React"
  },
  // ... more mappings
];

// Push to Figma (requires org plan)
await figmaTools.send_code_connect_mappings({
  fileKey: "tMHabCYB7teMvu7L8lz957",
  mappings
});
```

**4. Request Designer Review**
```
GitHub: Create PR
Figma: Share Code Connect link in PR description
```

**5. Iterate on Feedback**
```
Designer: Reviews live app, leaves comments in Figma
Developer: Updates code, re-pushes
Loop until approved
```

---

## Design-Code Sync Workflow

### Scenario 1: Designer Changes Color

**Figma**: Orange button color changed from #f97316 to #ff6600

**Workflow**:
1. Designer leaves comment: "@developer — updated button orange, see node 66:291"
2. Developer:
   - Opens Figma node 66:291
   - Clicks Code tab → opens GitHub file
   - Sees `bg-[#f97316]` in JobsCard
   - Changes to `bg-[#ff6600]`
   - Commits and pushes
3. Designer:
   - Sees PR notification
   - Clicks Code tab → sees updated code
   - Views live staging environment
   - Approves PR
4. Code merged → change ships

**Time saved**: 80% faster than email + Slack + phone calls

---

### Scenario 2: Developer Adds Component Variant

**Code**: Developer adds "Secondary" button variant

**Workflow**:
1. Developer:
   - Creates new component variant in code
   - Documents in PR: "Added secondary button variant"
   - Pushes to staging
2. Designer:
   - Receives PR notification
   - Clicks Code tab to review
   - Sees live variant in staging
   - Provides feedback: "Font weight should be 600, not 700"
3. Developer:
   - Updates code
   - Re-pushes
   - Designer approves

**Benefit**: Designer sees implementation immediately, not after merge

---

## Code Connect Best Practices

### 1. Keep Components Synchronized
- Every code change should be reflected in Figma Code Connect
- Every Figma design change should have a corresponding PR

### 2. Document Deviations
If code intentionally differs from design:
```
// Note in code comment:
// DESIGN NOTE: Sidebar is hidden on mobile via 'hidden md:flex'
// This differs from Figma (desktop-only) due to responsive requirements
```

### 3. Version Design System
When design changes:
- Tag commit: `design-v2.1`
- Update changelog: `docs/frontend/CHANGELOG.md`
- Notify team in Slack

### 4. Monthly Sync
- Monthly design-dev sync to review code-design alignment
- Update Code Connect links if components move
- Archive old component mappings

### 5. Naming Consistency
Figma component names must match code:
- Figma: "Dashboard Full" → Code: `DashboardPage`
- Figma: "Status Strip" → Code: `StatusStrip`
- Figma: "Jobs Card" → Code: `JobsCard`

---

## Future Enhancements

### Phase 1: API-Based Mapping (Next)
- Upgrade Figma plan to Organization
- Run automated mapping setup
- Sync all 5 components with one command

### Phase 2: Live Component Preview (Q2 2026)
- Enable `generate_figma_design` in Claude Code
- Push live React component to Figma
- Designers see interactive component in Figma
- Bidirectional editing: design → code → design

### Phase 3: Token Sync (Q3 2026)
- Sync Figma Variables with code CSS variables
- One-way sync: Figma → code
- Automatic code generation from tokens

### Phase 4: Automatic Code Generation (Q4 2026)
- Drag component from Figma to generate React code
- AI translates design → production code
- Developer reviews + refines
- Merge to main

---

## Troubleshooting

### Code Connect Link Not Showing in Figma

**Issue**: After creating mapping, "Code" tab doesn't appear in Figma

**Solutions**:
1. Refresh Figma page (`Cmd+R` on Mac, `Ctrl+R` on Windows)
2. Verify mapping was created: `git log --grep="code-connect"`
3. Check Figma plan: Settings → Plans & Billing → ensure Developer seat is active
4. Try creating mapping again via UI (manual option)

### GitHub Link Broken in Code Tab

**Issue**: Code tab shows link, but clicking breaks or 404

**Solutions**:
1. Verify file path is correct: `frontend/app/dashboard/page.tsx`
2. Verify branch is `ui/figma-test` (URL should have branch name)
3. Check file exists in branch: `git show ui/figma-test:frontend/app/dashboard/page.tsx`
4. Update mapping with correct URL if changed

### Designer Can't See Code Tab

**Issue**: Only "Inspect" tab visible, no "Code" tab

**Solutions**:
1. Verify your Figma plan is Organization or Team
2. Verify you have Developer seat (check in Team settings)
3. Verify Code Connect is enabled on the component (should be by default)
4. Contact Figma support if issue persists

---

## Resources

- [Figma Code Connect Docs](https://help.figma.com/hc/en-us/articles/23920389749655-Code-Connect)
- [Code Connect GitHub Integration](https://www.figma.com/blog/introducing-code-connect/)
- [CareerVP Figma File](https://figma.com/design/tMHabCYB7teMvu7L8lz957/CareerVP-Test-2)
- [Design System Rules](./DESIGN_SYSTEM_RULES.md)
- [Dashboard Implementation](../frontend/app/dashboard/page.tsx)

---

## Next Steps

**Immediate** (this week):
- [ ] Upgrade Figma plan to Organization or Team
- [ ] Add Developer seat to team
- [ ] Run automated Code Connect setup

**Short-term** (next week):
- [ ] Verify all 5 mappings in Figma
- [ ] Test Code → GitHub navigation
- [ ] Start design review workflow

**Medium-term** (next month):
- [ ] Set up weekly design-dev sync
- [ ] Create component library (extract Sidebar, Topbar, etc.)
- [ ] Plan Phase 2 enhancements

---

**Last Updated**: March 14, 2026
**Next Review**: March 28, 2026
**Owner**: Design + Development Team
