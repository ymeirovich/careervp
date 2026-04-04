# Implementation Plan: P0 — Replace Figma MCP Asset URLs

**Spec**: `spec_P0_figma_asset_fix.yaml`
**Priority**: P0 (ship first)
**Owner**: frontend

---

## Problem Summary

Three dashboard components embed live Figma CDN URLs as decorative icons:
- `Topbar.tsx` → dropdown arrow (user chip)
- `Sidebar.tsx` → logo
- `StatusStrip.tsx` → active status dot

Every page render triggers HTTP requests to `figma.com/api/mcp/asset/*` — fails in CI/offline/corporate networks.

---

## Files to Modify

| File | Current | Change |
|------|---------|--------|
| `frontend/components/dashboard/Topbar.tsx:6-7` | `const ASSET_DROPDOWN_ARROW = "https://..."` | Remove constant, replace `<img>` with inline chevron SVG |
| `frontend/components/dashboard/Sidebar.tsx:7-8` | `const ASSET_CVP_LOGO = "https://..."` | Remove constant, replace `<img>` with local SVG |
| `frontend/components/dashboard/StatusStrip.tsx:4-5` | `const ASSET_STATUS_DOT = "https://..."` | Remove constant, replace `<img>` with inline circle SVG |

---

## Files to Create

| File | Description |
|------|-------------|
| `frontend/public/assets/dropdown-arrow.svg` | 14×14 chevron down (flip with `scaleY(-1)` as original) |
| `frontend/public/assets/careervp-logo.svg` | 30×30 logo, export from Figma |
| `frontend/public/assets/status-dot.svg` | 16×16 green circle |

**Note**: Topbar arrow and status dot can be inline SVGs (simpler, no network request). Sidebar logo requires actual export.

---

## Implementation Steps

### Step 1: Create local SVG assets
- [ ] Export `careervp-logo.svg` from Figma (file key: 661cfe6f, node requires lookup)
- [ ] Create `dropdown-arrow.svg` (chevron)
- [ ] Create `status-dot.svg` (green circle)

### Step 2: Modify Topbar.tsx
- [ ] Remove `ASSET_DROPDOWN_ARROW` constant (lines 6-7)
- [ ] Replace `<img src={ASSET_DROPDOWN_ARROW}>` with inline `<svg>` or `<img src="/assets/dropdown-arrow.svg">`
- [ ] Keep existing `style={{ transform: "scaleY(-1)" }}` for chevron direction

### Step 3: Modify Sidebar.tsx
- [ ] Remove `ASSET_CVP_LOGO` constant (lines 7-8)
- [ ] Replace `<img src={ASSET_CVP_LOGO}>` with `<img src="/assets/careervp-logo.svg">`
- [ ] Keep existing className and alt

### Step 4: Modify StatusStrip.tsx
- [ ] Remove `ASSET_STATUS_DOT` constant (lines 4-5)
- [ ] Replace `<img src={ASSET_STATUS_DOT}>` with inline `<span className="w-4 h-4 rounded-full bg-[#16b44b]" />` (CSS circle)
- [ ] Or: use `<img src="/assets/status-dot.svg">`

### Step 5: Add prevention
- [ ] Add ESLint rule to warn on figma.com URLs in src/href
- [ ] Document in CLAUDE.md: "Do not commit Figma MCP asset URLs"

---

## Verification Commands

```bash
# Static: no Figma URLs in components
grep -r "figma.com/api/mcp/asset" frontend/components/ && echo "FAIL" || echo "PASS"

# Static: no Figma URLs in app/
grep -r "figma.com/api/mcp/asset" frontend/app/ && echo "FAIL" || echo "PASS"

# Live: open DevTools → Network → filter figma.com → load dashboard → should show 0 requests
```

---

## Acceptance Criteria

| ID | Description | Gate |
|----|-------------|------|
| AC-P0-01 | Zero figma.com requests on dashboard load | post_deploy |
| AC-P0-02 | Constants removed from source | pre_merge |
| AC-P0-03 | Icons render visually | post_deploy |
| AC-P0-04 | No figma.com URLs in frontend/ | pre_merge |
| AC-P0-05 | CI linting check passes | pre_merge |

---

## Rollback

```bash
git revert <commit>  # No DB or infra changes
```

---

## Notes

- **Topbar arrow**: Original uses `scaleY(-1)` to flip chevron. Either pre-flip the SVG or keep the transform.
- **Status dot**: Can replace with CSS-only circle (`<span className="w-4 h-4 rounded-full bg-[#16b44b]" />`) — simpler than SVG.
- **Sidebar logo**: Must export from Figma — requires file access. May need user to provide the export.