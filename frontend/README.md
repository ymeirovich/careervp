# CareerVP Test1 — Figma Implementation

Interactive celebration page built from the CareerVP Figma design with a **CSS design system** for maintainable color tokens.

**Stacks Available:**
- **React:** Next.js 15 App Router · Tailwind CSS v3 · CSS Variables Design System
- **Vanilla:** `standalone.html` — Pure HTML/CSS/JS (no build step)

## Quick Start

### Local Preview

```bash
npm install
npm run dev
```

Visit **http://localhost:3000** and click the button to trigger the fireworks.

### Deploy to Vercel (Shareable Link)

The fastest way to share this page:

1. **Push to GitHub** (if not already):
   ```bash
   git add frontend/
   git commit -m "feat: add CareerVP Test1 page"
   git push origin develop
   ```

2. **Deploy to Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new)
   - Select "Import Git Repository"
   - Choose your repo (`ymeirovich/careervp`)
   - Set "Root Directory" to `frontend/`
   - Click "Deploy"

3. **Share** the auto-generated URL (e.g., `https://careervp-test1-xyz.vercel.app`)

---

## What's Implemented

✓ **Desktop-1 → Desktop-2** transition (click button → show fireworks)
✓ **CSS Design System** — Figma tokens mapped to CSS variables (easily updatable)
✓ **Figma design tokens** mapped to CSS variables:
  - `--color-bg: #1a1a2e` (dark navy background)
  - `--color-button-default: #f97316` (orange button)
  - `--color-button-click: #ffcc00` (yellow on click)
  - `--color-border: #000000` (black border)
✓ **Distinctive fonts** (DM Serif Display + DM Sans)
✓ **Tactile animations** (spring physics, 3-D shadows, grain texture)
✓ **Two implementations:**
  - **React:** Production-grade Next.js 15 + Tailwind
  - **Vanilla:** Standalone HTML (no build step)

---

## CSS Design System

All Figma design tokens are defined as CSS variables in `app/globals.css`:

```css
:root {
  --color-bg: #1a1a2e;           /* Dark navy background */
  --color-button-default: #f97316; /* Orange button */
  --color-button-click: #ffcc00;   /* Yellow on click */
  --color-border: #000000;         /* Black border */
}
```

**Component styles** use `@layer components`:

```css
.btn-careerVP {
  background-color: var(--color-button-default);
}

.btn-careerVP.clicked {
  background-color: var(--color-button-click);
}
```

To update colors, modify the `:root` variables in `app/globals.css` — all references update automatically.

---

## File Structure

```
frontend/
├── app/
│   ├── layout.tsx         ← Root layout + font setup
│   ├── page.tsx           ← Main interactive page (React)
│   └── globals.css        ← CSS design system + Tailwind
├── components/
│   └── ui/button.tsx      ← Button component
├── lib/
│   └── utils.ts           ← cn() utility
├── standalone.html        ← Vanilla HTML/CSS/JS version
├── package.json
├── tailwind.config.ts
└── next.config.js
```

---

## Vanilla HTML Version

For **no build step**, open `standalone.html` directly in your browser. It's identical to the React version:

```bash
open standalone.html  # macOS
start standalone.html # Windows
xdg-open standalone.html # Linux
```

Same CSS variables, animations, and interactions — zero dependencies.

---

## Figma Design

- **File:** CareerVP Test1 (`OAncxa2CNTZFvQ3gGrI79O`)
- **Frames:**
  - `Desktop-1` (1:14) — Orange button on cream
  - `Desktop-2` (3:5) — Fireworks reveal
  - `Button` (1:8) — Component with Default/Click states
