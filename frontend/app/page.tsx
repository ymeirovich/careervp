"use client";

/**
 * CareerVP Test1 — Figma Implementation
 * Stack: Next.js 15 App Router · Tailwind CSS v3 · CSS Design System
 *
 * Design Tokens from Figma (OAncxa2CNTZFvQ3gGrI79O):
 *   - Desktop-1  →  cream background + orange "Click This" button
 *   - Desktop-2  →  fireworks reveal on click (button turns yellow)
 *
 * CSS Variables: Mapped in @layer base in globals.css
 *   --color-bg: #f6eddc (Figma background)
 *   --color-button-default: #f97316 (Figma orange)
 *   --color-button-click: #ffcc00 (Figma yellow)
 *   --color-border: #000000 (Figma black border)
 */

import { useState } from "react";
import { DM_Serif_Display, DM_Sans } from "next/font/google";
import { cn } from "@/lib/utils";

// ─── Fonts ─────────────────────────────────────────────────────────────────
const displayFont = DM_Serif_Display({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
  display: "swap",
});

const sansFont = DM_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-sans",
  display: "swap",
});

// ─── Assets ────────────────────────────────────────────────────────────────
const FIREWORKS_SRC =
  "https://www.figma.com/api/mcp/asset/d930558f-3a56-483d-91c3-6355e90301e5";

// ─── Page ──────────────────────────────────────────────────────────────────
export default function CareerVPTest1() {
  const [clicked, setClicked] = useState(false);

  return (
    <main
      className={cn(
        displayFont.variable,
        sansFont.variable,
        "relative flex min-h-screen w-full select-none items-center justify-center overflow-hidden",
      )}
      style={{ backgroundColor: "var(--color-bg)" }}
    >
      {/* ── Grain texture overlay ── */}
      <div aria-hidden className="grain-texture" />

      {/* ── Radial glow (behind fireworks) ── */}
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-0 z-[2] transition-opacity duration-700",
          clicked ? "opacity-100" : "opacity-0",
        )}
        style={{
          background: `radial-gradient(ellipse 60% 60% at 60% 50%, rgba(249,115,22,0.18) 0%, transparent 70%)`,
        }}
      />

      {/* ── Desktop-2: Fireworks Reveal (Figma frame 3:5) ── */}
      <div
        className={cn(
          "absolute inset-0 z-[3] flex items-center justify-center transition-[opacity,transform] duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]",
          clicked
            ? "opacity-100 scale-100"
            : "opacity-0 scale-95 pointer-events-none",
        )}
      >
        {clicked && (
          <img
            src={FIREWORKS_SRC}
            alt="Fireworks celebration"
            width={500}
            height={500}
            className="h-[500px] w-[500px] rounded-2xl object-cover shadow-[0_32px_80px_rgba(0,0,0,0.35)]"
            style={{
              animation: "fireworks-pop 0.55s cubic-bezier(0.34,1.56,0.64,1) forwards",
            }}
          />
        )}
      </div>

      {/* ── Desktop-1 Button (Figma frame 1:14, instance 1:15) ── */}
      <div className="relative z-10 flex flex-col items-center gap-4">
        <button
          onClick={() => setClicked((v) => !v)}
          className={cn("btn-careerVP", clicked && "clicked")}
        >
          Click This
        </button>

        {/* Hint label (fades on click) */}
        <p
          className={cn(
            "font-[family-name:var(--font-sans)] text-sm font-light tracking-widest uppercase text-black/40 transition-opacity duration-500",
            clicked ? "opacity-0" : "opacity-100",
          )}
        >
          go on, try it
        </p>
      </div>
    </main>
  );
}
