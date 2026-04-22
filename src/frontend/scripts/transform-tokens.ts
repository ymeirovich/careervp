import fs from 'fs';
import path from 'path';

interface FigmaToken {
  value: string;
  type: string;
  description?: string;
}

interface FigmaTokenGroup {
  [key: string]: FigmaToken | FigmaTokenGroup;
}

interface FigmaTokensFile {
  global: {
    colors: FigmaTokenGroup;
    spacing?: FigmaTokenGroup;
    radius?: FigmaTokenGroup;
  };
}

// Figma token path → CSS variable name
const COLOR_CSS_VAR: Record<string, string> = {
  'colors.background.page':   '--color-page-bg',
  'colors.surface.card':      '--color-card',
  'colors.surface.subtle':    '--color-surface-subtle',
  'colors.surface.selected':  '--color-surface-selected',
  'colors.surface.disabled':  '--color-surface-disabled',
  'colors.primary.action':    '--color-primary-action',
  'colors.text.primary':      '--color-text-primary',
  'colors.text.muted':        '--color-text-muted',
  'colors.text.subtle':       '--color-text-subtle',
  'colors.text.inverse':      '--color-text-inverse',
  'colors.border.default':    '--color-border-default',
  'colors.border.strong':     '--color-border-strong',
  'colors.state.active':      '--color-state-active',
  'colors.state.warning':     '--color-state-warning',
  'colors.state.error':       '--color-state-error',
  'colors.state.info':        '--color-state-info',
};

const RADIUS_CSS_VAR: Record<string, string> = {
  'radius.sm': '--radius-sm',
  'radius.md': '--radius-md',
  'radius.lg': '--radius-lg',
  'radius.xl': '--radius-xl',
};

function isToken(val: unknown): val is FigmaToken {
  return typeof val === 'object' && val !== null && 'value' in val && 'type' in val;
}

function flattenTokens(obj: FigmaTokenGroup, prefix = ''): Record<string, FigmaToken> {
  const result: Record<string, FigmaToken> = {};
  for (const [key, val] of Object.entries(obj)) {
    const dotPath = prefix ? `${prefix}.${key}` : key;
    if (isToken(val)) {
      result[dotPath] = val;
    } else {
      Object.assign(result, flattenTokens(val as FigmaTokenGroup, dotPath));
    }
  }
  return result;
}

function buildThemeBlock(
  colorTokens: Record<string, FigmaToken>,
  radiusTokens: Record<string, FigmaToken>,
): string {
  const lines: string[] = ['@theme {'];

  const colorSections: Record<string, string[]> = {};
  for (const [path, cssVar] of Object.entries(COLOR_CSS_VAR)) {
    const token = colorTokens[path];
    if (!token) continue;
    const section = path.split('.')[1];
    if (!colorSections[section]) colorSections[section] = [];
    colorSections[section].push(`  ${cssVar}: ${token.value};`);
  }

  let firstSection = true;
  for (const [section, vars] of Object.entries(colorSections)) {
    if (!firstSection) lines.push('');
    lines.push(`  /* Colors — ${section} */`);
    lines.push(...vars);
    firstSection = false;
  }

  const radiusVars = Object.entries(RADIUS_CSS_VAR)
    .map(([path, cssVar]) => {
      const token = radiusTokens[path];
      return token ? `  ${cssVar}: ${token.value}px;` : null;
    })
    .filter(Boolean) as string[];

  if (radiusVars.length > 0) {
    lines.push('');
    lines.push('  /* Border radius */');
    lines.push(...radiusVars);
  }

  lines.push('}');
  return lines.join('\n') + '\n';
}

function run(): void {
  const root = path.resolve(__dirname, '..');
  const tokensPath = path.join(root, 'figma-tokens.json');
  const tokensCSS = path.join(root, 'styles', 'tokens.css');

  if (!fs.existsSync(tokensPath)) {
    console.error(`figma-tokens.json not found at ${tokensPath}`);
    console.error('Export tokens from the Figma Tokens plugin first.');
    process.exit(1);
  }

  const raw = JSON.parse(fs.readFileSync(tokensPath, 'utf-8')) as FigmaTokensFile;
  const global = raw.global;

  const colorTokens = flattenTokens(global.colors ?? {}, 'colors');
  const radiusTokens = flattenTokens(global.radius ?? {}, 'radius');

  const themeBlock = buildThemeBlock(colorTokens, radiusTokens);
  fs.writeFileSync(tokensCSS, themeBlock, 'utf-8');
  console.log(`✓ tokens.css updated (${tokensCSS})`);

  const colorMap: Record<string, unknown> = {};
  for (const [dotPath, cssVar] of Object.entries(COLOR_CSS_VAR)) {
    const parts = dotPath.split('.').slice(1);
    let node = colorMap;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!node[parts[i]]) node[parts[i]] = {};
      node = node[parts[i]] as Record<string, unknown>;
    }
    node[parts[parts.length - 1]] = `var(${cssVar})`;
  }

  const radiusMap: Record<string, string> = {};
  for (const [dotPath, cssVar] of Object.entries(RADIUS_CSS_VAR)) {
    const key = dotPath.split('.')[1];
    radiusMap[key] = `var(${cssVar})`;
  }

  console.log('\nTailwind colors config (paste into tailwind.config.ts → theme.extend.colors):');
  console.log(JSON.stringify(colorMap, null, 2));
  console.log('\nTailwind borderRadius config (paste into theme.extend.borderRadius):');
  console.log(JSON.stringify(radiusMap, null, 2));
}

run();
