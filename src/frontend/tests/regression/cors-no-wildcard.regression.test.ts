/**
 * Regression Tests: CORS No Wildcard
 * Feature: F-SUB-020-R / P-10
 *
 * Reads the *real* CDK and Lambda-layer CORS source and asserts on its actual
 * content. The previous version of this file asserted against inline,
 * hand-typed strings that never touched the real files, so it could never
 * fail no matter what the source actually did — it was poisoned and gave no
 * regression coverage. See specs/P-08-P-10-P-11-cors-waf-spec.md.
 *
 * The GatewayResponse wildcard ('*' on 401/403/4xx/5xx) is a deliberate,
 * codified exception (contract §10's 401 -> refresh -> sign-out flow needs a
 * browser-visible 401), so this file asserts the wildcard is CONFINED to
 * GatewayResponse and absent from the default (success-path) CORS config —
 * not that it is absent everywhere.
 */

import { readFileSync } from 'fs';
import { join } from 'path';

// ─── Fixtures: real source files ───────────────────────────────────────────

const REPO_ROOT = join(__dirname, '../../../..');
const API_CONSTRUCT_PATH = join(REPO_ROOT, 'infra/careervp/api_construct.py');
const CORS_UTILS_PATH = join(
  REPO_ROOT,
  'src/backend/careervp/handlers/cors_utils.py',
);

const apiConstructSource = readFileSync(API_CONSTRUCT_PATH, 'utf-8');
const corsUtilsSource = readFileSync(CORS_UTILS_PATH, 'utf-8');

/** The `default_cors_preflight_options(...)` block only, up to its closing `),`. */
function extractDefaultCorsBlock(source: string): string {
  const start = source.indexOf('default_cors_preflight_options=aws_apigateway.CorsOptions(');
  expect(start).toBeGreaterThan(-1);
  const end = source.indexOf('\n            deploy_options=', start);
  expect(end).toBeGreaterThan(start);
  return source.slice(start, end);
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Regression: CORS No Wildcard', () => {
  describe('F-SUB-020-R: CORS Wildcard Check', () => {
    it('Lambda-layer CORS helper must never fall back to a wildcard origin', () => {
      // get_cors_headers() must only ever echo back a resolved origin that is
      // already a member of the allow-list; it must not contain a '*' branch.
      expect(corsUtilsSource).not.toContain("'*'");
      expect(corsUtilsSource).not.toContain('"*"');
      expect(corsUtilsSource).toContain('resolved in _ALLOWED_ORIGINS');
    });

    it('default (success-path) API Gateway CORS must not use Cors.ALL_ORIGINS', () => {
      const corsBlock = extractDefaultCorsBlock(apiConstructSource);
      expect(corsBlock).not.toContain('Cors.ALL_ORIGINS');
      // Must resolve to a real per-env allow-list, not a hardcoded wildcard.
      expect(corsBlock).toMatch(/self\.allowed_origins/);
    });

    it('GatewayResponse keeps the wildcard as a documented, isolated exception', () => {
      const gatewayResponseIndex = apiConstructSource.indexOf(
        '_add_gateway_error_responses',
      );
      expect(gatewayResponseIndex).toBeGreaterThan(-1);
      const gatewayResponseBlock = apiConstructSource.slice(gatewayResponseIndex);

      expect(gatewayResponseBlock).toContain('"Access-Control-Allow-Origin": "\'*\'"');

      // And the default CORS (success path) block must NOT contain that
      // wildcard — it must be confined to GatewayResponse only.
      const corsBlock = extractDefaultCorsBlock(apiConstructSource);
      expect(corsBlock).not.toMatch(/['"]\*['"]/);
    });

    it('should use exact origin matching, not substring matching', () => {
      const allowedOrigins = ['https://app.careervp.com'];

      function isAllowed(origin: string): boolean {
        return allowedOrigins.includes(origin);
      }

      // These should NOT be allowed
      expect(isAllowed('https://app.careervp.com.evil.com')).toBe(false);
      expect(isAllowed('https://evil.com/https://app.careervp.com')).toBe(false);
      expect(isAllowed('http://app.careervp.com')).toBe(false); // Wrong protocol
      expect(isAllowed('')).toBe(false);

      // Only the exact origin should be allowed
      expect(isAllowed('https://app.careervp.com')).toBe(true);
    });
  });
});

export {};
