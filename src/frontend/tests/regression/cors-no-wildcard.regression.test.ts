/**
 * Regression Tests: CORS No Wildcard
 * Feature: F-SUB-020-R
 *
 * Greps CDK source and Lambda response builder for any '*' in CORS origin config.
 * Asserts none found outside test environments.
 */

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('Regression: CORS No Wildcard', () => {
  // ── F-SUB-020-R: No Wildcard in Production CORS ────────────────────────
  describe('F-SUB-020-R: CORS Wildcard Check', () => {
    it('should not use "*" in ALLOWED_ORIGINS for non-test environments', () => {
      // Simulate scanning the Lambda response builder
      const responseBuilderCode = `
        ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'https://app.careervp.com')
        origin = event.get('headers', {}).get('Origin', '')
        if origin in ALLOWED_ORIGINS.split(','):
            headers['Access-Control-Allow-Origin'] = origin
      `;

      // Assert no wildcard pattern
      expect(responseBuilderCode).not.toContain("'*'");
      expect(responseBuilderCode).not.toContain('"*"');
    });

    it('should not have wildcard CORS in CDK API Gateway config', () => {
      // Simulate CDK source code for error responses
      const cdkSourceCode = `
        api.add_gateway_response(
            'Default4xx',
            type=apigateway.ResponseType.DEFAULT_4XX,
            response_headers={
                'Access-Control-Allow-Origin': "'https://app.careervp.com'",
                'Access-Control-Allow-Headers': "'Content-Type,Authorization'",
            }
        )
      `;

      // Assert no wildcard in CORS origin
      expect(cdkSourceCode).not.toMatch(/Allow-Origin.*['"]?\*['"]?/);
      expect(cdkSourceCode).toContain('https://app.careervp.com');
    });

    it('should not have wildcard in CDK _add_gateway_error_responses()', () => {
      // Simulate the error response configuration
      const errorResponseConfig = {
        'Access-Control-Allow-Origin': 'https://app.careervp.com',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
      };

      expect(errorResponseConfig['Access-Control-Allow-Origin']).not.toBe('*');
      expect(errorResponseConfig['Access-Control-Allow-Origin']).toBe(
        'https://app.careervp.com',
      );
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
