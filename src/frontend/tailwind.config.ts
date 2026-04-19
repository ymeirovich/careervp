import type { Config } from 'tailwindcss';

// In Tailwind v4 the primary token source is styles/tokens.css (@theme block).
// This file extends with semantic aliases that map to those CSS variables,
// matching the spec-01 naming structure.
const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './stories/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: { page: 'var(--color-page-bg)' },
        surface: {
          card: 'var(--color-card)',
          subtle: 'var(--color-surface-subtle)',
          selected: 'var(--color-surface-selected)',
          disabled: 'var(--color-surface-disabled)',
        },
        primary: { action: 'var(--color-primary-action)' },
        text: {
          primary: 'var(--color-text-primary)',
          muted: 'var(--color-text-muted)',
          subtle: 'var(--color-text-subtle)',
          inverse: 'var(--color-text-inverse)',
        },
        border: {
          default: 'var(--color-border-default)',
          strong: 'var(--color-border-strong)',
        },
        state: {
          active: 'var(--color-state-active)',
          warning: 'var(--color-state-warning)',
          error: 'var(--color-state-error)',
          info: 'var(--color-state-info)',
        },
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
