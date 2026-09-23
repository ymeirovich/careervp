/**
 * Cognito configuration resolution for the SPA.
 *
 * There are deliberately no defaults here. These values used to fall back to the DEV
 * user pool and app client, which meant a devx or staging build with a missing or
 * misspelled env var authenticated against dev and looked completely healthy — nothing
 * logged, no request failed, and there was no way to tell which environment a session
 * actually belonged to. Missing config is now a hard failure at the point of use.
 *
 * Resolution is lazy rather than module-level so the failure surfaces as a real error
 * from the auth path (and in tests) instead of breaking module import during SSR or
 * static analysis.
 */

/**
 * Each getter below reads `process.env.NEXT_PUBLIC_*` as a literal, static property
 * access. Next.js/webpack inlines `NEXT_PUBLIC_*` values at build time by pattern-matching
 * that exact syntactic form; it cannot see through a dynamic `process.env[name]` lookup,
 * because the substitution is a compile-time text replacement, not a real runtime object.
 * A dynamic lookup silently resolves to `undefined` in every browser bundle regardless of
 * what's configured in the deploy environment — do not refactor this into a loop or a
 * `names.map(n => process.env[n])`-style helper.
 */
function requireValue(value: string | undefined, ...names: string[]): string {
  if (value !== undefined && value.trim() !== '') {
    return value.trim();
  }
  throw new Error(
    `Missing required Cognito configuration: ${names.join(' or ')}. ` +
      'Set it for this environment — there is no default, because falling back would ' +
      'silently authenticate against a different environment.',
  );
}

export function getUserPoolId(): string {
  return requireValue(
    process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
    'NEXT_PUBLIC_COGNITO_USER_POOL_ID',
  );
}

export function getClientId(): string {
  return requireValue(
    process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID ?? process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID,
    'NEXT_PUBLIC_COGNITO_APP_CLIENT_ID',
    'NEXT_PUBLIC_COGNITO_CLIENT_ID',
  );
}

export function getCognitoDomain(): string {
  return requireValue(
    process.env.NEXT_PUBLIC_COGNITO_DOMAIN,
    'NEXT_PUBLIC_COGNITO_DOMAIN',
  ).replace(/\/$/, '');
}

export function getPoolConfig(): { UserPoolId: string; ClientId: string } {
  return { UserPoolId: getUserPoolId(), ClientId: getClientId() };
}
