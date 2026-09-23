/**
 * P-07 (step 1.6) — auth config must fail loudly, never fall back to the DEV pool.
 *
 * scope_lock_clause: P-07
 *
 * Why this exists: `lib/pkce.ts` and `lib/auth.ts` resolve the Cognito user-pool id
 * and app-client id with `?? '<hardcoded dev value>'`. A devx (or staging) build with a
 * missing or typo'd env var therefore authenticates against the **dev** pool and looks
 * completely healthy. That is a silent cross-environment auth failure: nothing logs, no
 * request errors, and "which environment did I just test?" becomes unanswerable.
 *
 * The contract: missing config is a hard failure, not a default.
 */

import * as fs from 'fs';
import * as path from 'path';

const DEV_POOL_ID = 'us-east-1_WiHMRqLpe';
const DEV_CLIENT_ID = '7blipbarsisbctqh6hlsj46sqa';

const LIB_DIR = path.resolve(__dirname, '..', '..', 'lib');

const COGNITO_ENV_KEYS = [
  'NEXT_PUBLIC_COGNITO_USER_POOL_ID',
  'NEXT_PUBLIC_COGNITO_APP_CLIENT_ID',
  'NEXT_PUBLIC_COGNITO_CLIENT_ID',
  'NEXT_PUBLIC_COGNITO_DOMAIN',
];

function withEnv(overrides: Record<string, string | undefined>, run: () => void): void {
  const saved: Record<string, string | undefined> = {};
  for (const key of COGNITO_ENV_KEYS) {
    saved[key] = process.env[key];
  }
  try {
    for (const key of COGNITO_ENV_KEYS) {
      const value = overrides[key];
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
    jest.resetModules();
    run();
  } finally {
    for (const key of COGNITO_ENV_KEYS) {
      if (saved[key] === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = saved[key];
      }
    }
    jest.resetModules();
  }
}

function walkSourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === 'dist') continue;
      out.push(...walkSourceFiles(full));
    } else if (/\.tsx?$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

describe('P-07 step 1.6 — auth configuration hardening', () => {
  it('test_pkce_config_throws_when_pool_id_env_missing', () => {
    withEnv(
      {
        NEXT_PUBLIC_COGNITO_USER_POOL_ID: undefined,
        NEXT_PUBLIC_COGNITO_APP_CLIENT_ID: 'some-client',
        NEXT_PUBLIC_COGNITO_CLIENT_ID: 'some-client',
        NEXT_PUBLIC_COGNITO_DOMAIN: 'https://example.auth.us-east-1.amazoncognito.com',
      },
      () => {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const auth = require('../../lib/auth');
        expect(() => auth.getCurrentCognitoUser()).toThrow(
          /NEXT_PUBLIC_COGNITO_USER_POOL_ID/,
        );
      },
    );
  });

  it('test_pkce_config_throws_when_client_id_env_missing', () => {
    withEnv(
      {
        NEXT_PUBLIC_COGNITO_USER_POOL_ID: 'us-east-1_example00',
        NEXT_PUBLIC_COGNITO_APP_CLIENT_ID: undefined,
        NEXT_PUBLIC_COGNITO_CLIENT_ID: undefined,
        NEXT_PUBLIC_COGNITO_DOMAIN: 'https://example.auth.us-east-1.amazoncognito.com',
      },
      () => {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const pkce = require('../../lib/pkce');
        expect(() => pkce.hostedUiLogoutUrl('https://db-redesign.example.com')).toThrow(
          /NEXT_PUBLIC_COGNITO_(APP_)?CLIENT_ID/,
        );
      },
    );
  });

  it('test_pkce_config_throws_when_cognito_domain_env_missing', () => {
    withEnv(
      {
        NEXT_PUBLIC_COGNITO_USER_POOL_ID: 'us-east-1_example00',
        NEXT_PUBLIC_COGNITO_APP_CLIENT_ID: 'some-client',
        NEXT_PUBLIC_COGNITO_CLIENT_ID: 'some-client',
        NEXT_PUBLIC_COGNITO_DOMAIN: undefined,
      },
      () => {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const pkce = require('../../lib/pkce');
        expect(() => pkce.hostedUiLogoutUrl('https://db-redesign.example.com')).toThrow(
          /NEXT_PUBLIC_COGNITO_DOMAIN/,
        );
      },
    );
  });

  it('test_no_hardcoded_dev_pool_or_client_in_frontend_lib', () => {
    const offenders: string[] = [];
    for (const file of walkSourceFiles(LIB_DIR)) {
      const source = fs.readFileSync(file, 'utf-8');
      if (source.includes(DEV_POOL_ID) || source.includes(DEV_CLIENT_ID)) {
        offenders.push(path.relative(LIB_DIR, file));
      }
    }
    expect(offenders).toEqual([]);
  });
});
