import { describe, expect, it } from 'vitest';

import { createPkceAuthorizationRequest } from '../../lib/pkce';

describe('P-07 authorization code with PKCE', () => {
  it('test_p07_frontend_sign_in_uses_code_pkce', async () => {
    const request = await createPkceAuthorizationRequest({
      email: 'person@example.com',
      origin: 'https://dev.careervp.com',
      cognitoDomain: 'https://careervp-dev.auth.us-east-1.amazoncognito.com',
      clientId: 'public-spa-client',
    });

    const url = new URL(request.authorizationUrl);
    expect(url.pathname).toBe('/oauth2/authorize');
    expect(url.searchParams.get('response_type')).toBe('code');
    expect(url.searchParams.get('code_challenge_method')).toBe('S256');
    expect(url.searchParams.get('code_challenge')).not.toBe(request.codeVerifier);
    expect(url.searchParams.get('redirect_uri')).toBe('https://dev.careervp.com/callback');
    expect(url.searchParams.get('client_id')).toBe('public-spa-client');
    expect(url.searchParams.get('login_hint')).toBe('person@example.com');
    expect(request.codeVerifier.length).toBeGreaterThanOrEqual(43);
    expect(request.state.length).toBeGreaterThanOrEqual(32);
  });
});
