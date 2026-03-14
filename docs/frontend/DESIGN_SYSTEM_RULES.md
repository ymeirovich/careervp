# CareerVP Design System Rules

**Last Updated**: March 14, 2026
**Source**: Figma file `tMHabCYB7teMvu7L8lz957` (CareerVP Test 2)
**Reference Frame**: Node 66:262 "Desktop / Dashboard Full"

---

## Framework & Tech Stack

- **Frontend Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS v3
- **Typography**: DM Sans (body), DM Serif Display (display)
- **Languages**: TypeScript 5.6+
- **Package Manager**: npm
- **Node Version**: 18+

---

## Design Tokens (Extracted from Figma)

### Color Palette

| Token Name | Hex Value | CSS Implementation | Usage | Figma Variable |
|---|---|---|---|---|
| **Page Background** | #fcf7f5 | `style={{ backgroundColor: "#fcf7f5" }}` | Page wrapper, main background | `color/background/page` |
| **Card Surface** | #FFFFFF | `bg-white` | Sidebar, topbar, cards, surfaces | `color/surface/card` |
| **App Shell** | #FAFAFA | `bg-[#fafafa]` | Main app container, secondary background | - |
| **Border Default** | #CBD5E1 | `border-[#cbd5e1]` | All borders, dividers, rules | `color/border/default` |
| **Text Primary** | #1E2229 | `text-[#1e2229]` | Primary text, headings, body | `color/text/primary` |
| **Text Muted** | #6B7280 | `text-[#6b7280]` | Secondary text, hints, labels | `color/text/muted` |
| **State Active** | #16B44B | `text-[#16b44b]` | Active status, success states, green dots | `state/active` |
| **Primary Action** | #F97316 | `bg-[#f97316]` | CTA buttons, primary interactive elements | `color/primary/action` |
| **Active Nav BG** | rgba(217,217,217,0.61) | `bg-[rgba(217,217,217,0.61)]` | Active navigation item background | - |
| **Status Strip BG** | rgba(245,245,245,0.61) | `bg-[rgba(245,245,245,0.61)]` | Status card backgrounds | - |

### Spacing & Sizing Scale

| Size | Value | Tailwind Class | Usage |
|---|---|---|---|
| **xs** | 4px | `gap-1`, `p-1` | Micro spacing |
| **sm** | 8px | `gap-2`, `p-2` | Small spacing |
| **md** | 16px | `gap-4`, `p-4` | Medium spacing |
| **lg** | 24px | `gap-6`, `p-6` | Large spacing, section gaps |
| **xl** | 32px | `gap-8`, `p-8` | Extra large spacing |

### Component Sizes

| Component | Size (px) | Tailwind Class | Usage |
|---|---|---|---|
| **Sidebar Width** | 240 | `w-60` | Left navigation sidebar |
| **Topbar Height** | 80 | `h-20` | Top navigation bar |
| **Logo (SVG)** | 30×30 | `h-[30px] w-[30px]` | CareerVP logo in sidebar |
| **Status Dot** | 16×16 | `h-4 w-4` | Active status indicator |
| **Dropdown Arrow** | 22×22 | `h-[14px] w-[14px]` | User menu dropdown icon |

### Typography Scale

| Element | Font | Size | Weight | Line Height | Letter Spacing | Tailwind |
|---|---|---|---|---|---|---|
| **Page Title** (Dashboard) | DM Sans | 24px | semibold (600) | normal | - | `text-2xl font-semibold` |
| **Card Title** (My Jobs) | DM Sans | 18px | bold (700) | normal | - | `text-lg font-bold` |
| **Subheading** | DM Sans | 16px | bold (700) | normal | - | `text-base font-bold` |
| **Body Text** | DM Sans | 14px | normal (400) | normal | - | `text-sm font-normal` |
| **Label/Caption** | DM Sans | 12px | medium (500) | normal | 0.05em | `text-xs font-medium` |
| **Table Header** | DM Sans | 14px | medium (500) | normal | - | `text-sm font-medium` |
| **Table Data** | DM Sans | 14px | medium (500) | normal | - | `text-sm font-medium` |
| **Nav Items** | DM Sans | 14px | bold (700) | normal | - | `text-sm font-bold` |

---

## Component Architecture

### Page Structure: DashboardPage

**File**: `frontend/app/dashboard/page.tsx`

```
DashboardPage (root component)
│
├── Page Wrapper
│   └── backgroundColor: #fcf7f5
│
└── App Shell (flex container)
    ├── backgroundColor: #fafafa
    ├── border: 1px #cbd5e1
    ├── width: 1239px
    ├── height: 900px
    │
    ├─── Sidebar (240px wide)
    │    ├── backgroundColor: white
    │    ├── borderRight: 1px #cbd5e1
    │    │
    │    ├── Logo Section
    │    │   ├── CVP Icon (30×30, orange, rounded)
    │    │   └── "CareerVP" Text (32px, bold)
    │    │
    │    ├── Divider
    │    │   └── border-b: 1px #cbd5e1
    │    │
    │    └── Navigation
    │        ├── CareerVP (section title, 14px)
    │        ├── Dashboard (active, bg: rgba(217,217,217,0.61))
    │        ├── Applications
    │        ├── CV Center
    │        ├── Billing
    │        └── Settings
    │
    └─── Content Area (flex-1)
         ├── Topbar (80px)
         │   ├── backgroundColor: white
         │   ├── borderBottom: 1px #cbd5e1
         │   ├── Left: "Dashboard" (24px, semibold)
         │   └── Right: "Credits: 1 / 3" + User Menu
         │
         └── Main Content (flex column, gap-6)
             ├── StatusStrip
             │   ├── backgroundColor: white
             │   ├── border: 1px #cbd5e1
             │   ├── borderRadius: 8px
             │   ├── display: flex, gap: 32px
             │   │
             │   ├── Card 1: Plan
             │   │   └── "Plan: Free Tier"
             │   │
             │   ├── Card 2: Credits
             │   │   └── "Credits Remaining: 1 / 3"
             │   │
             │   └── Card 3: Status
             │       ├── "Status: Active" (green #16b44b)
             │       └── Status Dot (green, 16×16)
             │
             └── JobsCard
                 ├── backgroundColor: white
                 ├── border: 1px #cbd5e1
                 ├── borderRadius: 8px
                 │
                 ├── Header Section
                 │   ├── "My Jobs" (18px, bold)
                 │   └── "+ New Application" Button
                 │       ├── backgroundColor: #f97316
                 │       ├── color: white
                 │       ├── borderRadius: 8px
                 │       ├── padding: 12px × 8px
                 │
                 └── Jobs Table
                     ├── Table Header Row
                     │   ├── backgroundColor: #cbd5e1
                     │   ├── color: #6b7280
                     │   ├── font-weight: medium
                     │   └── Columns:
                     │       ├── Job Title (flex-1)
                     │       ├── Company (160px)
                     │       ├── Status (120px)
                     │       ├── Updated (140px)
                     │       └── Action (140px)
                     │
                     └── Table Data Row(s)
                         ├── border-b: 1px #e2e8f0
                         ├── padding: 12px × 16px
                         ├── hover: bg-[rgba(245,245,245,0.5)]
                         ├── Data:
                         │   ├── "Learning Experience Specialist"
                         │   ├── "SysAid"
                         │   ├── "Active" (green #16b44b)
                         │   ├── "Mar 7, 2026"
                         │   └── "View Application" (link)
```

---

## Component Functions

### 1. Sidebar()
```typescript
function Sidebar() {
  // Renders left navigation sidebar
  // Props: none (currently static)
  // Returns: aside element with navigation
  // Key styling:
  // - Width: 240px (w-60)
  // - Background: white
  // - Border right: #cbd5e1
}
```

**Design Spec**:
- Logo: 30×30 orange rounded square + "CareerVP" text (32px, bold)
- Divider: 1px #cbd5e1 border
- Nav items: 14px, bold, with active state bg
- Active item: `bg-[rgba(217,217,217,0.61)]`

### 2. Topbar()
```typescript
function Topbar() {
  // Renders top navigation bar
  // Left: "Dashboard" page title
  // Right: Credits display + User menu
  // Key styling:
  // - Height: 80px (h-20)
  // - Background: white
  // - Border bottom: #cbd5e1
}
```

**Design Spec**:
- Title: 24px, semibold, #1e2229
- Credits: 16px, normal, #1e2229
- User Menu: gray background (#f0f2f5), rounded border
- Flex: `justify-between`

### 3. StatusStrip()
```typescript
function StatusStrip() {
  // Renders plan/credits/status indicator
  // 3 status cards in horizontal flex
  // Key styling:
  // - Layout: flex, gap-8
  // - Card bg: rgba(245,245,245,0.61)
  // - Card border: #cbd5e1
  // - Border radius: 8px
}
```

**Design Spec**:
- 3 cards: Plan, Credits Remaining, Status
- Status text: #16b44b (green) for "Active"
- Status dot: 16×16 green indicator
- All cards: 14px font, bold text

### 4. JobsCard()
```typescript
function JobsCard() {
  // Renders jobs table card
  // Header + Table structure
  // Key styling:
  // - Background: white
  // - Border: #cbd5e1, border-radius: 8px
  // - Table header bg: #cbd5e1
  // - Table rows: gap-4, border-b: #e2e8f0
}
```

**Design Spec**:
- Title: 18px, bold, #1e2229
- Button: Orange #f97316, white text, rounded
- Table columns: Job Title (flex-1), Company (160px), Status (120px), Updated (140px), Action (140px)
- Status: green #16b44b for "Active"

---

## Design-to-Code Translation Guide

### Rule 1: Colors
**When designer changes a color in Figma:**

1. Find the color in the Figma design
2. Extract the hex value (e.g., #f97316)
3. Search codebase: `grep -r "#f97316" frontend/`
4. Replace with new hex in Tailwind class
5. Test: verify the change renders correctly

**Example:**
```
Figma: Button orange changed from #f97316 to #ff6600
Code: bg-[#f97316] → bg-[#ff6600]
```

### Rule 2: Spacing
**When designer changes gaps or padding in Figma:**

1. Measure the spacing in Figma (pixels)
2. Convert to Tailwind: 4px=gap-1, 8px=gap-2, 16px=gap-4, 24px=gap-6, 32px=gap-8
3. Update the class in code
4. Verify layout in browser

**Example:**
```
Figma: Section gap changed from 24px to 32px
Code: gap-6 → gap-8
```

### Rule 3: Typography
**When designer changes font size or weight in Figma:**

1. Check the font size (pixels) and weight
2. Map to Tailwind: text-xs (12px), text-sm (14px), text-base (16px), text-lg (18px), text-2xl (24px)
3. Map weight: font-normal, font-medium, font-semibold, font-bold
4. Update the class

**Example:**
```
Figma: Title changed from 24px semibold to 28px bold
Code: text-2xl font-semibold → text-[28px] font-bold
```

### Rule 4: Layout Changes
**When designer changes flex direction or alignment in Figma:**

1. Check the layout in Figma (flex row/column, alignment)
2. Update Tailwind: flex-row, flex-col, justify-start, justify-between, items-center, etc.
3. Test responsive behavior

**Example:**
```
Figma: Topbar changed from space-between to gap-4
Code: justify-between → gap-4 justify-start
```

---

## Responsive Design Rules

### Current: Desktop Only
The dashboard is currently designed for desktop (1440px width).

### Future: Mobile Support
When adding mobile, follow:

1. **Breakpoints** (Tailwind):
   - Mobile: 375px (no prefix, base styles)
   - Tablet: 768px (`md:` prefix)
   - Desktop: 1024px+ (`lg:` prefix)

2. **Sidebar on Mobile**:
   - Hidden by default: `hidden md:flex`
   - Or: Mobile hamburger menu (future)

3. **Table on Mobile**:
   - Card layout instead of table
   - Single column, stacked rows

4. **Topbar on Mobile**:
   - Compact credits display
   - Drawer menu for user menu

---

## Code Connect Mappings

These mappings link Figma design components to code implementations. Once Code Connect is set up, designers can click any Figma component and see the exact React file that implements it.

### Mapping Status

| Figma Node ID | Component Name | File Path | Function Name | Status | Figma URL |
|---|---|---|---|---|---|
| **66:262** | Dashboard Full | `frontend/app/dashboard/page.tsx` | `DashboardPage` | ⏳ Ready to map | node 66:262 |
| **66:264** | Sidebar | `frontend/app/dashboard/page.tsx` | `Sidebar` | ⏳ Ready to map | node 66:264 |
| **66:278** | Topbar | `frontend/app/dashboard/page.tsx` | `Topbar` | ⏳ Ready to map | node 66:278 |
| **66:287** | Status Strip | `frontend/app/dashboard/page.tsx` | `StatusStrip` | ⏳ Ready to map | node 66:287 |
| **66:291** | Jobs Card | `frontend/app/dashboard/page.tsx` | `JobsCard` | ⏳ Ready to map | node 66:291 |

**Note**: Mappings require Figma Organization/Enterprise plan with Developer seat. Currently awaiting plan upgrade.

---

## Asset Management

### Figma Assets (7-day expiration)

These asset URLs are valid for 7 days from extraction (extracted March 14, 2026, valid until March 21, 2026):

| Asset | URL | Size | Usage | Notes |
|---|---|---|---|---|
| **CVP Logo** | `https://www.figma.com/api/mcp/asset/661cfe6f-1041-4faa-8666-3d001bb92746` | 30×30 | Sidebar logo | Orange rounded square |
| **Status Dot** | `https://www.figma.com/api/mcp/asset/62714d3b-6e61-40cf-917d-9ad5f45735ac` | 16×16 | Active status indicator | Green circular dot |
| **Dropdown Arrow** | `https://www.figma.com/api/mcp/asset/29ba343a-ed50-4f60-ab33-814b014f47b8` | 22×22 | User menu dropdown | Polygon shape, inverted |

### Permanent Asset Storage

For production use, export assets from Figma and store in repo:

```
frontend/public/icons/
├── cvp-logo.svg          (replace Figma asset URL)
├── status-dot.svg        (replace Figma asset URL)
└── dropdown-arrow.svg    (replace Figma asset URL)
```

**Export Steps**:
1. In Figma, right-click asset
2. Select "Export"
3. Choose SVG format
4. Save to `frontend/public/icons/`
5. Update image `src` in code

---

## Tailwind Configuration

**File**: `frontend/tailwind.config.ts`

```typescript
const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],      // DM Sans
        display: ["var(--font-display)", "Georgia", "serif"],       // DM Serif Display
      },
      colors: {
        // Custom colors from Figma
        // Add if needed for reusable theme colors
      },
    },
  },
  plugins: [],
};
```

**Font Variables** (set in `app/layout.tsx`):
- `--font-sans`: DM Sans (400, 500 weights)
- `--font-display`: DM Serif Display (400 weight)

---

## Best Practices

### 1. Naming Conventions
- Components: PascalCase (`DashboardPage`, `StatusStrip`)
- Functions: camelCase (`getJobsData`, `formatDate`)
- CSS classes: kebab-case (`text-primary`, `border-default`)
- Files: kebab-case (`dashboard-page.tsx`) or PascalCase (`DashboardPage.tsx`)

### 2. Component Organization
Currently: All components in `page.tsx` for simplicity
Future: Extract to separate files in `components/` for reusability

```
components/
├── Sidebar.tsx
├── Topbar.tsx
├── StatusStrip.tsx
└── JobsCard.tsx
```

### 3. Styling Approach
- **Tailwind first**: Use Tailwind classes for all styling
- **Arbitrary values**: For custom colors/sizes not in Tailwind: `bg-[#fcf7f5]`, `w-[240px]`
- **Inline styles**: Only for dynamic values or temporary overrides
- **CSS variables**: For theme switching (future enhancement)

### 4. TypeScript Usage
```typescript
// Define types for components
interface Job {
  id: number;
  title: string;
  company: string;
  status: "Active" | "Draft" | "Archived";
  updated: string;
}

// Use generics for reusable components
function StatusBadge<T extends string>(status: T) { ... }
```

### 5. Accessibility
- Use semantic HTML: `<aside>`, `<nav>`, `<table>`, `<button>`
- Add `aria-*` attributes where needed
- Ensure color contrast meets WCAG standards
- Keyboard navigation support

### 6. Performance
- Use `React.memo()` for components that don't frequently update
- Lazy load images using `next/image`
- Avoid inline arrow functions in JSX (use `useCallback`)

---

## Testing Checklist

Before shipping design changes:

- [ ] Colors match Figma hex values exactly
- [ ] Spacing matches Figma measurements (pixels/gaps)
- [ ] Typography sizes and weights match Figma
- [ ] Component layout matches Figma structure
- [ ] Interactions work (buttons clickable, links work)
- [ ] Responsive behavior matches design intent
- [ ] No console errors or warnings
- [ ] Accessibility standards met (keyboard nav, ARIA labels)

---

## Future Enhancements

### Phase 1: Code Connect Integration
- [ ] Set up Code Connect mappings (requires org upgrade)
- [ ] Designers can click Figma → see code
- [ ] Developers see Figma links in IDE

### Phase 2: Component Library
- [ ] Extract components to separate files
- [ ] Create Storybook for component docs
- [ ] Build component library (`ui/Button.tsx`, `ui/Card.tsx`, etc.)

### Phase 3: Design Token System
- [ ] Convert colors to CSS variables
- [ ] Convert spacing to CSS custom properties
- [ ] Sync Figma Variables with code

### Phase 4: Responsive Design
- [ ] Add mobile layouts (375px breakpoint)
- [ ] Tablet layouts (768px breakpoint)
- [ ] Mobile navigation (hamburger menu)

### Phase 5: Bidirectional Workflow
- [ ] Push live component screenshots to Figma
- [ ] Real-time collaboration between designer and developer
- [ ] Auto-generate code from Figma designs

---

## Useful Commands

```bash
# Start development server
cd frontend && npm run dev

# Build for production
npm run build

# Run linting
npm run lint

# Type check
npx tsc --noEmit
```

---

## References

- **Figma File**: [CareerVP Test 2](https://figma.com/design/tMHabCYB7teMvu7L8lz957/CareerVP-Test-2)
- **Design Frame**: Node 66:262 "Desktop / Dashboard Full"
- **Frontend Directory**: `frontend/`
- **Dashboard Page**: `frontend/app/dashboard/page.tsx`
