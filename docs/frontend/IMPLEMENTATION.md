# Dashboard Implementation Details

**Date**: March 14, 2026
**Branch**: `ui/figma-test`
**Source**: Figma node 66:262 (Desktop / Dashboard Full)
**File**: `frontend/app/dashboard/page.tsx`

---

## Overview

The CareerVP Dashboard is a React component that displays:
- User's job applications
- Plan and credit status
- Navigation sidebar
- Application management interface

**Technology Stack**:
- Next.js 15 (App Router)
- Tailwind CSS v3
- TypeScript
- React 19

---

## Component Hierarchy

```
DashboardPage (main export)
├── Sidebar()
│   ├── Logo section (30×30 icon + text)
│   ├── Divider
│   └── Navigation list
│       ├── CareerVP (section title)
│       ├── Dashboard (active)
│       ├── Applications
│       ├── CV Center
│       ├── Billing
│       └── Settings
│
├── Content Area (flex-1)
│   ├── Topbar()
│   │   ├── Page title: "Dashboard"
│   │   └── Right section
│   │       ├── Credits display
│   │       └── User menu
│   │
│   └── Main Content (flex column, gap-6, padding-6)
│       ├── StatusStrip()
│       │   ├── Plan Card: "Plan: Free Tier"
│       │   ├── Credits Card: "Credits Remaining: 1 / 3"
│       │   └── Status Card: "Status: Active ●"
│       │
│       └── JobsCard()
│           ├── Header
│           │   ├── "My Jobs" title
│           │   └── "+ New Application" button
│           │
│           └── Jobs Table
│               ├── Table Header
│               │   ├── Job Title (flex-1)
│               │   ├── Company (160px)
│               │   ├── Status (120px)
│               │   ├── Updated (140px)
│               │   └── Action (140px)
│               │
│               └── Table Rows
│                   └── Job data (currently 1 sample row)
```

---

## Component Breakdown

### 1. DashboardPage (Root Component)

**Purpose**: Assembles entire dashboard layout

**Props**: None (currently static)

**Renders**:
```
Page wrapper (background #fcf7f5)
  └─ App Shell (bordered #fafafa)
     ├─ Sidebar (240px)
     └─ Content Area (flex-1)
        ├─ Topbar (80px)
        └─ Main (flex column, gap-6, padding-6)
```

**Key Styling**:
```typescript
// Page background
style={{ backgroundColor: "#fcf7f5" }}

// App shell
className="mx-auto flex border border-[#cbd5e1] bg-[#fafafa]"
style={{ marginLeft: "100px", marginTop: "62px", width: "1239px", minHeight: "900px" }}

// Content area
className="flex flex-1 flex-col min-w-0"
```

**Data Flow**: Static data (no API calls yet)

---

### 2. Sidebar()

**Purpose**: Left navigation menu

**Props**: None

**Renders**:
- Logo section: CVP icon (30×30) + "CareerVP" text
- Divider: 1px border
- Navigation list: 5 items (Dashboard active, others inactive)

**Key Styling**:
```typescript
className="flex w-[220px] shrink-0 flex-col bg-white border-r border-[#cbd5e1]"
```

**Navigation Items**:
```typescript
const NAV_ITEMS = [
  { label: "CareerVP", isSection: true },
  { label: "Dashboard", active: true, href: "/dashboard" },
  { label: "Applications", href: "#" },
  { label: "CV Center", href: "#" },
  { label: "Billing", href: "#" },
  { label: "Settings", href: "#" },
];
```

**Active Item Styling**:
```typescript
"active" in item && item.active
  ? "bg-[rgba(217,217,217,0.61)]"  // Light gray active state
  : "hover:bg-[rgba(217,217,217,0.3)]"  // Hover state
```

---

### 3. Topbar()

**Purpose**: Top navigation bar with page title and user menu

**Props**: None

**Renders**:
- Left: "Dashboard" title (24px, semibold)
- Right: "Credits: 1 / 3" + User menu ("Lisi" + dropdown)

**Key Styling**:
```typescript
className="flex h-20 shrink-0 items-center justify-between border-b border-[#cbd5e1] bg-white px-6"
```

**Elements**:
- Title: `text-2xl font-semibold text-[#1e2229]`
- Credits: `text-base font-normal`
- User Menu: `rounded-[8px] border border-[#6b7280] bg-[#f0f2f5]`

**Dropdown Arrow**: Inverted polygon image (ASSET_DROPDOWN_ARROW)

---

### 4. StatusStrip()

**Purpose**: Display plan, credits, and status information

**Props**:
- `plan`: string (default "Free Tier")
- `creditsUsed`: number (default 1)
- `creditsTotal`: number (default 3)

**Renders**: 3 status cards in horizontal flex

**Status Cards**:
1. **Plan Card**: "Plan: Free Tier"
2. **Credits Card**: "Credits Remaining: 1 / 3" (with progress bar)
3. **Status Card**: "Status: Active" + green dot (green #16b44b)

**Key Styling**:
```typescript
// Container
className="flex items-center gap-8 rounded-[8px] border border-[#cbd5e1] bg-white px-[26px] py-[11px] w-full"

// Cards
className="flex items-center justify-center rounded-[4px] border border-[#cbd5e1] bg-[rgba(245,245,245,0.61)] px-4 py-3"

// Status text (green)
className="text-[#16b44b]"
```

**Progress Bar** (Credits):
```typescript
<div className="h-1.5 w-20 rounded-full bg-stone-100 overflow-hidden">
  <div
    className="h-full rounded-full bg-[#f97316]"
    style={{ width: `${(creditsUsed / creditsTotal) * 100}%` }}
  />
</div>
```

---

### 5. JobsCard()

**Purpose**: Display job applications in a table format

**Props**: None

**Renders**:
- Header: "My Jobs" title + "+ New Application" button
- Table: Header row + data rows

**Table Structure**:
```
Header Row (bg-[#cbd5e1]):
├─ Job Title (flex-1, variable width)
├─ Company (160px, fixed)
├─ Status (120px, fixed)
├─ Updated (140px, fixed)
└─ Action (140px, fixed)

Data Row(s) (hover: bg-[rgba(245,245,245,0.5)]):
├─ "Learning Experience Specialist"
├─ "SysAid"
├─ "Active" (green #16b44b)
├─ "Mar 7, 2026"
└─ "View Application" (link)
```

**Button Styling** ("+ New Application"):
```typescript
className="inline-flex items-center rounded-[8px] bg-[#f97316] px-3 py-2 transition-opacity"

// Hover & Active states
"hover:opacity-90 active:opacity-80"
```

**Table Row Hover**:
```typescript
className="hover:bg-[rgba(245,245,245,0.5)] transition-colors"
```

---

## Design Tokens Used

### Colors

| Usage | Hex | Tailwind | Location |
|---|---|---|---|
| Page BG | #fcf7f5 | inline style | DashboardPage wrapper |
| Card BG | white | `bg-white` | Sidebar, Topbar, Cards |
| App Shell BG | #fafafa | `bg-[#fafafa]` | App Shell container |
| Border | #cbd5e1 | `border-[#cbd5e1]` | All borders |
| Text Primary | #1e2229 | `text-[#1e2229]` | Headings, primary text |
| Text Muted | #6b7280 | `text-[#6b7280]` | Secondary text, table header |
| Active State | #16b44b | `text-[#16b44b]` | "Active" status, green dot |
| Primary CTA | #f97316 | `bg-[#f97316]` | "+ New Application" button |
| Active Nav BG | rgba(217,217,217,0.61) | `bg-[rgba(217,217,217,0.61)]` | Dashboard nav item |
| Status Card BG | rgba(245,245,245,0.61) | `bg-[rgba(245,245,245,0.61)]` | Status cards |

### Typography

| Element | Font | Size | Weight | Tailwind |
|---|---|---|---|---|
| Page Title | DM Sans | 24px | semibold | `text-2xl font-semibold` |
| Card Title | DM Sans | 18px | bold | `text-lg font-bold` |
| Nav Items | DM Sans | 14px | bold | `text-sm font-bold` |
| Body Text | DM Sans | 14-16px | normal/medium | `text-sm` / `text-base` |
| Table Header | DM Sans | 14px | medium | `text-sm font-medium` |

### Spacing

| Element | Size | Tailwind | Usage |
|---|---|---|---|
| Sidebar Width | 240px | `w-[220px]` | Left nav |
| Topbar Height | 80px | `h-20` | Top bar |
| Main Gap | 24px | `gap-6` | Between sections |
| Main Padding | 24px | `p-6` | Content padding |
| Card Padding | 12px × 16px | `px-4 py-3` | Card internals |
| Logo Size | 30×30px | `h-[30px] w-[30px]` | Sidebar icon |
| Status Dot | 16×16px | `h-4 w-4` | Status indicator |

---

## Data Structure

### Jobs Array

```typescript
interface Job {
  id: number;           // Unique identifier
  title: string;        // Job title
  company: string;      // Company name
  status: JobStatus;    // "Active" | "Draft" | "Archived"
  updated: string;      // Last updated date (e.g., "Mar 7, 2026")
}

const JOBS: Job[] = [
  {
    id: 1,
    title: "Learning Experience Specialist",
    company: "SysAid",
    status: "Active",
    updated: "Mar 7, 2026",
  },
  // More jobs here (currently just 1 sample)
];
```

### Navigation Items Array

```typescript
const NAV_ITEMS = [
  { label: "CareerVP", isSection: true },
  { label: "Dashboard", active: true, href: "/dashboard" },
  { label: "Applications", href: "#" },
  { label: "CV Center", href: "#" },
  { label: "Billing", href: "#" },
  { label: "Settings", href: "#" },
];
```

### Table Columns Array

```typescript
const TABLE_COLUMNS = [
  { key: "title", label: "Job Title", className: "flex-1 min-w-0" },
  { key: "company", label: "Company", className: "w-[160px] shrink-0" },
  { key: "status", label: "Status", className: "w-[120px] shrink-0" },
  { key: "updated", label: "Updated", className: "w-[140px] shrink-0" },
  { key: "action", label: "Action", className: "w-[140px] shrink-0" },
];
```

---

## Assets & External Resources

### Figma Asset URLs (7-day expiration)

```typescript
const ASSET_CVP_LOGO =
  "https://www.figma.com/api/mcp/asset/661cfe6f-1041-4faa-8666-3d001bb92746";
const ASSET_STATUS_DOT =
  "https://www.figma.com/api/mcp/asset/62714d3b-6e61-40cf-917d-9ad5f45735ac";
const ASSET_DROPDOWN_ARROW =
  "https://www.figma.com/api/mcp/asset/29ba343a-ed50-4f60-ab33-814b014f47b8";
```

**Usage**:
```typescript
<img src={ASSET_CVP_LOGO} className="h-[30px] w-[30px]" />
<img src={ASSET_STATUS_DOT} className="h-4 w-4" />
<img src={ASSET_DROPDOWN_ARROW} style={{ transform: "scaleY(-1)" }} />
```

**Future**: Export from Figma and store in `frontend/public/icons/`

---

## Layout Dimensions

### Page/Frame Dimensions (Figma)

```
┌──────────────────────────────────────────────────────┐
│ Page: "Test 2 Desktop"                               │
│ Frame: "Desktop / Dashboard Full"                    │
│ Node ID: 66:262                                      │
│                                                       │
│ Viewport: 1440×1024px                               │
│ App Shell:                                           │
│   Position: left 100px, top 62px                    │
│   Size: 1239×900px                                   │
│   Border: 1px #cbd5e1                               │
│   Background: #fafafa                               │
│                                                       │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Sidebar      │ Content Area                     │ │
│ │ 240px wide   │ flex-1                           │ │
│ │              │                                  │ │
│ │ Logo         │ Topbar (80px)                   │ │
│ │ Nav          │ ┌─────────────────────────────┐│ │
│ │              │ │ Dashboard   Credits  Menu   ││ │
│ │              │ └─────────────────────────────┘│ │
│ │              │                                  │ │
│ │              │ Main (gap-6, p-6)              │ │
│ │              │ ┌─────────────────────────────┐│ │
│ │              │ │ Status Strip                 ││ │
│ │              │ ├─────────────────────────────┤│ │
│ │              │ │ Jobs Card                    ││ │
│ │              │ │ ┌──────────────────────────┐││ │
│ │              │ │ │ My Jobs  [+ New App]     │││ │
│ │              │ │ ├──────────────────────────┤││ │
│ │              │ │ │ Table                    │││ │
│ │              │ │ └──────────────────────────┘││ │
│ │              │ └─────────────────────────────┘│ │
│ │              │                                  │ │
│ └─────────────────────────────────────────────────┘ │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Component Heights & Widths

| Component | Width | Height | Notes |
|---|---|---|---|
| Sidebar | 240px | 900px | Full height of app shell |
| Topbar | flex-1 | 80px | Spans remaining width |
| Main Content | flex-1 | auto | Fills remaining space |
| Status Strip | 924px | auto | Cards: 48px each |
| Jobs Card | 924px | auto | Header: 72px + Table |
| Table Header | 904px | 55px | With padding |
| Table Row | 904px | 78px | With padding & border |

---

## Responsive Behavior (Current)

**Currently**: Desktop-only (1440px width design)

**Breakpoints Ready for Future**:
- Mobile: 375px (base, no prefix)
- Tablet: 768px (`md:` Tailwind prefix)
- Desktop: 1024px+ (`lg:` Tailwind prefix)

**Responsive Enhancements**:
- Sidebar: hide on mobile (`hidden md:flex`)
- Table: convert to cards on mobile
- Topbar: simplify on mobile
- Grid: adjust columns on mobile

---

## Performance Considerations

### Current
- Static data (no API calls)
- Single page load
- All components inline (no code splitting)
- Images from Figma (temporary URLs)

### Future Optimizations
1. Code split components (`React.lazy()`)
2. Paginate table rows (currently 1 row)
3. Cache Figma assets locally
4. Implement virtual scrolling for large tables
5. Add loading states and error boundaries

---

## Testing Checklist

Before shipping:

- [ ] Colors match Figma exactly (#f97316, #1e2229, etc.)
- [ ] Spacing matches measurements (24px gaps, 80px topbar, 240px sidebar)
- [ ] Typography matches (24px semibold, 14px medium, etc.)
- [ ] Layout matches Figma structure
- [ ] All links navigate correctly
- [ ] Buttons are clickable
- [ ] Hover states visible (table rows, nav items)
- [ ] No console errors
- [ ] No accessibility warnings
- [ ] Responsive behavior matches intent (if mobile layouts added)

---

## Future Enhancements

### Phase 1: Code Connect (Done)
- [x] Implement dashboard from Figma design
- [x] Document design tokens
- [ ] Set up Code Connect mappings

### Phase 2: Data Integration (Next)
- [ ] Replace static JOBS with API calls
- [ ] Implement real job applications list
- [ ] Add loading states
- [ ] Add error handling
- [ ] Pagination for large lists

### Phase 3: Interactivity
- [ ] "+ New Application" button → modal form
- [ ] "View Application" links → detail page
- [ ] Nav items → actual page navigation
- [ ] User menu → dropdown menu

### Phase 4: Features
- [ ] Filter jobs by status
- [ ] Sort jobs by date/company
- [ ] Search jobs
- [ ] Edit job details
- [ ] Delete applications

### Phase 5: Responsive Design
- [ ] Mobile sidebar (hamburger menu)
- [ ] Mobile table (card layout)
- [ ] Mobile navigation
- [ ] Touch-friendly interactions

---

## File Locations

- **Main File**: `frontend/app/dashboard/page.tsx`
- **Layout**: `frontend/app/layout.tsx`
- **Global CSS**: `frontend/app/globals.css`
- **Tailwind Config**: `frontend/tailwind.config.ts`
- **Utilities**: `frontend/lib/utils.ts`

---

## Design System References

- **Colors**: `docs/frontend/DESIGN_SYSTEM_RULES.md` (Color Palette section)
- **Typography**: `docs/frontend/DESIGN_SYSTEM_RULES.md` (Typography Scale section)
- **Spacing**: `docs/frontend/DESIGN_SYSTEM_RULES.md` (Spacing Scale section)
- **Code Connect**: `docs/frontend/CODE_CONNECT_SETUP.md`
- **Workflow**: `docs/frontend/FIGMA_WORKFLOW_GUIDE.md`

---

**Last Updated**: March 14, 2026
**Status**: Ready for Code Connect integration
**Next Review**: After Code Connect plan upgrade
