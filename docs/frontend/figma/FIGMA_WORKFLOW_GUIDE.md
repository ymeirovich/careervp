# Figma ↔ Code Bidirectional Workflow Guide

**For**: Designers and Developers
**Purpose**: Maximize efficiency through synchronized design-code workflow
**Status**: Ready to activate

---

## Quick Start: Your First Day

### For Designers

**9 AM: Open Figma File**
1. Go to [CareerVP Test 2](https://figma.com/design/tMHabCYB7teMvu7L8lz957/CareerVP-Test-2)
2. Open page: "Test 2 Desktop"
3. Select component: "Desktop / Dashboard Full"

**10 AM: View Implementation**
1. Right panel → "Code" tab (once Code Connect is set up)
2. Click "View on GitHub" → see exact React code
3. Bookmark the link for future reference

**11 AM: Start Design Review**
1. Compare Figma design with GitHub code
2. Verify colors match: #f97316 (orange), #1e2229 (text), etc.
3. Verify spacing matches: 24px gaps, 80px topbar, 240px sidebar
4. Note any discrepancies

**12 PM: Request Changes (if needed)**
1. Add comment on Figma component
2. Example: "@developer — button padding should be 12px, currently 10px"
3. Developer gets notification immediately

**2 PM: Test Live App**
1. Open http://localhost:3000/dashboard
2. Compare live app with Figma design
3. Test interactions: click buttons, hover states, scroll table

### For Developers

**9 AM: Receive Design**
1. Designer shares Figma file link
2. Bookmark Code Connect setup doc: `docs/frontend/CODE_CONNECT_SETUP.md`
3. Read Design System Rules: `docs/frontend/DESIGN_SYSTEM_RULES.md`

**10 AM: Extract Design Context**
1. Use Claude Code to read Figma design
2. Extract colors, spacing, typography, layout
3. Save to notes: colors.md, spacing.md, typography.md

**11 AM: Implement Component**
1. Create `frontend/app/dashboard/page.tsx`
2. Use exact design tokens from Figma
3. Build component structure to match Figma layout

**12 PM: Test Implementation**
1. Start dev server: `npm run dev`
2. Visit http://localhost:3000/dashboard
3. Compare with Figma design
4. Iterate until colors, spacing, typography match exactly

**2 PM: Set Up Code Connect**
1. Create Code Connect mappings (once plan is upgraded)
2. Link Figma nodes to React functions
3. Share GitHub links with designer
4. Designer can now click Figma → see code

---

## The Design-Code Feedback Loop

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  1. DESIGNER                                        │
│     ├─ Creates mockup in Figma                      │
│     ├─ Specifies colors, spacing, typography       │
│     └─ Adds detailed notes & measurements          │
│                           ↓                          │
│  2. DEVELOPER                                       │
│     ├─ Reads design context from Figma             │
│     ├─ Implements React components                 │
│     └─ Uses exact design tokens (colors, spacing)  │
│                           ↓                          │
│  3. CODE CONNECT                                    │
│     ├─ Maps Figma nodes → React functions          │
│     ├─ Links code files in Figma                   │
│     └─ Enables bidirectional visibility            │
│                           ↓                          │
│  4. DESIGNER REVIEWS CODE                           │
│     ├─ Clicks Figma component → sees code          │
│     ├─ Views live app implementation               │
│     ├─ Compares with original design               │
│     └─ Requests changes if needed                  │
│                           ↓                          │
│  5. DEVELOPER ITERATES                             │
│     ├─ Reads designer comments in Figma            │
│     ├─ Updates code                                │
│     ├─ Re-pushes live app                          │
│     └─ Designer approves                           │
│                           ↓                          │
│  6. MERGE & SHIP                                    │
│     ├─ PR merged to main                           │
│     ├─ Deployed to production                      │
│     └─ Code Connect remains active                 │
│                           ↓                          │
│  [REPEAT for next feature]                         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Detailed Workflow Scenarios

### Scenario 1: New Feature Launch (1 Week)

#### Monday: Design Phase

**Designer Tasks**:
1. Create mockup in Figma
   - Layout: sidebar, topbar, content area
   - Colors: use brand palette (#f97316, #1e2229, etc.)
   - Typography: 24px for titles, 14px for body
   - Spacing: 24px gaps, 80px topbar
2. Create component variants
   - Button (Primary, Secondary, Disabled)
   - Card (Default, Hover)
   - Status Badge (Active, Inactive)
3. Add annotations
   - Measurements in pixels
   - Color hex values
   - Font sizes and weights
4. Share with developer via email/Slack

**Developer Tasks**:
1. Review Figma design
2. Ask clarification questions
3. Plan component structure
4. Check tech stack: Next.js, Tailwind, TypeScript

#### Tuesday-Wednesday: Implementation Phase

**Developer Tasks**:
1. Extract design context from Figma
   ```
   - Colors: #f97316, #1e2229, #cbd5e1, etc.
   - Spacing: 24px gaps, 80px height, 240px width
   - Typography: DM Sans, 24px semibold, 14px normal
   ```
2. Create components with exact design tokens
   ```typescript
   // frontend/app/dashboard/page.tsx
   export function DashboardPage() {
     return (
       <div style={{ backgroundColor: "#fcf7f5" }}>
         {/* Exact colors and spacing from Figma */}
       </div>
     );
   }
   ```
3. Test implementation
   - http://localhost:3000/dashboard
   - Compare colors: pick tool to verify hex
   - Compare spacing: measure in browser dev tools
   - Compare typography: check font size/weight

#### Thursday: Code Connect Setup

**Developer Tasks**:
1. Create Code Connect mappings
   - Map Dashboard → `frontend/app/dashboard/page.tsx`
   - Map Sidebar → `Sidebar` function
   - Map Topbar → `Topbar` function
   - etc.
2. Push code to `ui/figma-test` branch
3. Create GitHub PR
4. Share Code Connect links with designer

**Designer Tasks**:
1. Receive PR notification
2. Click Code tab in Figma → view code
3. Click "View on GitHub" → see implementation
4. Visit live staging: http://staging.example.com/dashboard
5. Compare with original Figma design

#### Friday: Review & Approval

**Designer Tasks**:
1. Final design review
   - Colors match exactly? ✓
   - Spacing matches? ✓
   - Typography matches? ✓
2. Test interactions
   - Buttons clickable? ✓
   - Hover states visible? ✓
3. Add comments if refinements needed
4. Approve PR when satisfied

**Developer Tasks**:
1. Address any designer feedback
2. Re-push changes if needed
3. Once approved:
   - Merge PR to main
   - Deploy to production
   - Code Connect links stay active

**Result**: Feature shipped with perfect design-code alignment

---

### Scenario 2: Design System Evolution

**Problem**: You have 50 components. How do you track which are implemented in code?

**Solution: Code Connect Matrix**

```
┌─────────────────────────────────────────┐
│ Component         │ Code File     │ Sync │
├─────────────────────────────────────────┤
│ Button/Primary    │ Button.tsx    │  ✓   │
│ Button/Secondary  │ Button.tsx    │  ✓   │
│ Button/Disabled   │ Button.tsx    │  ✓   │
│ Card              │ Card.tsx      │  ✓   │
│ Badge             │ Badge.tsx     │  ⚠️  │ ← Designer changed color
│ Input             │ Input.tsx     │  ❌  │ ← Not yet implemented
│ ...               │ ...           │  ... │
└─────────────────────────────────────────┘
```

**Workflow**:
1. Designer updates Badge color in Figma
2. Figma Code Connect shows: "Badge.tsx"
3. Developer gets notified
4. Developer updates `components/Badge.tsx` color
5. Designer verifies in live app
6. Merged in 30 minutes

**Without Code Connect**: Designer guesses which file, sends Slack message, waits for response, developer makes change, designer verifies. **Total time: 4-6 hours**

---

### Scenario 3: Mobile Responsive Design

**Problem**: Desktop and mobile designs differ. How to keep them synchronized?

**Solution: Responsive Code Connect**

```
Figma:
├── Desktop Mockup (1440px)
│   └── Code Connect: frontend/app/dashboard/page.tsx (default)
└── Mobile Mockup (375px)
    └── Code Connect: frontend/app/dashboard/page.tsx (responsive)
```

**Code Structure**:
```typescript
export function DashboardPage() {
  return (
    <div>
      {/* Desktop sidebar: visible by default */}
      <Sidebar className="hidden md:flex" />

      {/* Mobile hamburger: visible on mobile */}
      <MobileMenu className="md:hidden" />

      {/* Rest of content */}
    </div>
  );
}
```

**Workflow**:
1. Designer creates both desktop & mobile in Figma
2. Developer maps both to same React component
3. In Code Connect: designer sees both Figma variants → one code file
4. Designer reviews both on live app
5. Developer explains responsive logic: "hidden md:flex means sidebar is hidden on mobile, visible on desktop"

---

## Communication Patterns

### Designer → Developer

**Pattern 1: Request Change**
```
Figma Comment:
"@developer — button padding should be 14px (currently 10px)
See node 66:294 / Button element"

Developer can:
1. Click comment → opens Figma node
2. Click Code tab → sees Button.tsx
3. Search for padding value → finds it
4. Updates to 14px
5. Pushes code
6. Notifies designer
```

**Pattern 2: Suggest Refinement**
```
Live App Test:
"Tested dashboard at staging — sidebar looks great!
One thing: status indicator dot is too small.
Can we increase from 16px to 20px?"

Developer:
1. Opens Design System Rules
2. Finds Status Dot: 16×16
3. Changes to 20×20
4. Updates Figma Code Connect
5. Designer verifies in staging
```

### Developer → Designer

**Pattern 1: Request Design Review**
```
GitHub PR:
"Implemented dashboard from Figma design node 66:262.
Ready for design review at staging.example.com/dashboard
Figma Code Connect links:
- Dashboard: frontend/app/dashboard/page.tsx
- Sidebar: Sidebar()
- etc."

Designer:
1. Clicks Code links
2. Reviews GitHub code
3. Visits staging
4. Compares with Figma
5. Approves or requests changes
```

**Pattern 2: Clarify Design Intent**
```
GitHub Comment:
"Hi, I have a question about the sidebar navigation.
Should 'CareerVP' be a clickable link or just a label?
The Figma shows it as text, but UX-wise it could go back to home.
What's the intent?"

Designer:
"Great question! It should be a link to /home.
I'll update the Figma annotations to clarify."
```

---

## Tools & Shortcuts

### For Designers

**Figma Keyboard Shortcuts**:
- `Cmd+D` (Mac) / `Ctrl+D` (Windows): Duplicate component
- `Cmd+/` (Mac) / `Ctrl+/` (Windows): Search components
- `Shift+2`: Comment tool

**Figma Code Tab**:
- Right-click component → "Inspect" → "Code" tab
- Click file path → opens GitHub in new tab
- Click branch name → see other branches
- Bookmark GitHub URL for quick access

**Browser Shortcuts for Code Review**:
- Open Figma in one window
- Open GitHub in second window
- Open live app in third window
- Arrange side-by-side for comparison

### For Developers

**Extract Design Context**:
```bash
# Use Claude Code to read Figma design
# Command: Ask Claude to "extract design context from Figma node 66:262"
# Returns: colors, spacing, typography, assets, layout
```

**Compare Colors**:
```bash
# Browser DevTools
# Right-click element → Inspect → Styles
# Check background-color: #f97316
# Compare with Figma color: #f97316 ✓
```

**Measure Spacing**:
```bash
# Browser DevTools
# Right-click element → Inspect → Computed
# Check padding: 24px
# Check gap: 24px
# Compare with Figma measurements ✓
```

**Push to Staging**:
```bash
git push origin ui/figma-test
npm run build
# Deploy to staging.example.com
```

---

## Metrics & Success

### Track Design-Code Alignment

**Weekly Checklist**:
- [ ] Figma Code Connect links active in Figma? (should be 5/5)
- [ ] GitHub links navigate correctly? (should be 5/5)
- [ ] Colors match within 2% accuracy? (should be 100%)
- [ ] Spacing matches measurements? (should be 100%)
- [ ] Typography matches font size/weight? (should be 100%)
- [ ] Live app looks like Figma design? (subjective, but aim for 95%+)

**Monthly Metrics**:
- Time from design to code: target < 2 days
- Design review cycle time: target < 4 hours
- Revisions needed: target < 2 iterations
- Designer approval time: target < 24 hours
- Code-design sync issues: target 0

---

## FAQ

**Q: Can designer edit code directly in Figma?**
A: Currently no. Designer sees code (read-only), developer makes changes. Future: real-time collaborative editing.

**Q: What if developer implements feature differently than designed?**
A: Code Connect shows the code, designer sees the difference and can request changes via comments.

**Q: How do we handle design iterations?**
A: Both designer and developer iterate. Designer updates Figma, developer updates code, designer reviews live app. Repeat until perfect.

**Q: What if we need to A/B test design variants?**
A: Create both variants in Figma and code. Code Connect maps both → same component with prop variations.

**Q: Can we automate code generation from Figma?**
A: Coming soon (Phase 4 on roadmap). Currently: manual implementation with Code Connect sync.

**Q: How do we handle responsive design?**
A: Create both desktop & mobile in Figma. Code Connect maps both → one component file with responsive styles.

---

## Troubleshooting

### Designer: I don't see the "Code" tab in Figma

**Solution**:
1. Verify Figma plan is upgraded to Team/Organization ✓
2. Verify your team has Developer seat ✓
3. Refresh Figma page (Cmd+R)
4. Try opening component again
5. Check Figma settings: Settings → Plans & Billing

### Developer: Code Connect link broken or 404

**Solution**:
1. Verify file path in mapping is correct
2. Verify branch name matches (e.g., `ui/figma-test`)
3. Verify file exists: `git show branch:file-path`
4. Update mapping with correct URL
5. Push changes again

### Both: Live app doesn't match Figma design

**Solution**:
1. Use color picker to verify hex values
2. Use browser DevTools to measure spacing
3. Create issue with screenshot comparison
4. Discuss with partner during sync
5. Iterate until perfect

---

## Next Steps

### This Week
- [ ] Upgrade Figma plan to Team/Organization
- [ ] Set up Code Connect mappings
- [ ] Test Code → GitHub navigation
- [ ] Schedule design review session

### Next Week
- [ ] Launch first feature with Code Connect workflow
- [ ] Measure design-code alignment metrics
- [ ] Gather feedback from team
- [ ] Document learnings

### Next Month
- [ ] Refine workflow based on feedback
- [ ] Create component library
- [ ] Plan Phase 2 enhancements (live preview, token sync)

---

## Resources

- **Design System Rules**: `docs/frontend/DESIGN_SYSTEM_RULES.md`
- **Code Connect Setup**: `docs/frontend/CODE_CONNECT_SETUP.md`
- **Figma File**: [CareerVP Test 2](https://figma.com/design/tMHabCYB7teMvu7L8lz957/CareerVP-Test-2)
- **GitHub Repo**: [CareerVP](https://github.com/[your-org]/careervp)
- **Staging App**: http://staging.example.com/dashboard

---

**Last Updated**: March 14, 2026
**Owner**: Design + Development Team
**Review Schedule**: Weekly sync every Wednesday 2 PM
