import {
  CognitoAccessToken,
  CognitoIdToken,
  CognitoRefreshToken,
  CognitoUser,
  CognitoUserPool,
  CognitoUserSession,
} from 'amazon-cognito-identity-js';

const USER_POOL_ID =
  process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ?? 'us-east-1_WiHMRqLpe';
const CLIENT_ID =
  process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID ??
  process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ??
  '7blipbarsisbctqh6hlsj46sqa';
const COGNITO_DOMAIN =
  process.env.NEXT_PUBLIC_COGNITO_DOMAIN ||
  'https://careervp-dev.auth.us-east-1.amazoncognito.com';

const CODE_VERIFIER_KEY = 'careervp.pkce.code_verifier';
const OAUTH_STATE_KEY = 'careervp.pkce.state';

interface AuthorizationRequestOptions {
  email: string;
  origin: string;
  cognitoDomain: string;
  clientId: string;
}

interface AuthorizationRequest {
  authorizationUrl: string;
  codeVerifier: string;
  state: string;
}

interface TokenResponse {
  access_token: string;
  id_token: string;
  refresh_token: string;
}

function base64UrlEncode(bytes: Uint8Array): string {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join('');
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function randomValue(byteLength: number): string {
  const bytes = new Uint8Array(byteLength);
  crypto.getRandomValues(bytes);
  return base64UrlEncode(bytes);
}

async function codeChallenge(codeVerifier: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(codeVerifier));
  return base64UrlEncode(new Uint8Array(digest));
}

function normalizeDomain(domain: string): string {
  return domain.replace(/\/$/, '');
}

function callbackUri(origin: string): string {
  return process.env.NEXT_PUBLIC_COGNITO_REDIRECT_URI || `${origin}/callback`;
}

export async function createPkceAuthorizationRequest(
  options: AuthorizationRequestOptions,
): Promise<AuthorizationRequest> {
  const codeVerifier = randomValue(64);
  const state = randomValue(32);
  const authorizationUrl = new URL(`${normalizeDomain(options.cognitoDomain)}/oauth2/authorize`);
  authorizationUrl.search = new URLSearchParams({
    client_id: options.clientId,
    code_challenge: await codeChallenge(codeVerifier),
    code_challenge_method: 'S256',
    login_hint: options.email,
    redirect_uri: callbackUri(options.origin),
    response_type: 'code',
    scope: 'openid email phone profile aws.cognito.signin.user.admin',
    state,
  }).toString();

  return { authorizationUrl: authorizationUrl.toString(), codeVerifier, state };
}

export async function beginPkceSignIn(email: string): Promise<void> {
  const request = await createPkceAuthorizationRequest({
    email,
    origin: window.location.origin,
    cognitoDomain: COGNITO_DOMAIN,
    clientId: CLIENT_ID,
  });
  window.sessionStorage.setItem(CODE_VERIFIER_KEY, request.codeVerifier);
  window.sessionStorage.setItem(OAUTH_STATE_KEY, request.state);
  window.location.assign(request.authorizationUrl);
}

export async function completePkceSignIn(
  callbackUrl = window.location.href,
): Promise<{ token: string; user: CognitoUser }> {
  const url = new URL(callbackUrl);
  const oauthError = url.searchParams.get('error');
  if (oauthError) {
    throw new Error(url.searchParams.get('error_description') ?? oauthError);
  }

  const code = url.searchParams.get('code');
  const returnedState = url.searchParams.get('state');
  const expectedState = window.sessionStorage.getItem(OAUTH_STATE_KEY);
  const codeVerifier = window.sessionStorage.getItem(CODE_VERIFIER_KEY);
  if (!code || !returnedState || returnedState !== expectedState || !codeVerifier) {
    throw new Error('Invalid authorization callback');
  }

  const response = await fetch(`${normalizeDomain(COGNITO_DOMAIN)}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: CLIENT_ID,
      code,
      code_verifier: codeVerifier,
      grant_type: 'authorization_code',
      redirect_uri: callbackUri(window.location.origin),
    }),
  });
  if (!response.ok) {
    throw new Error('Authorization code exchange failed');
  }

  const tokens = (await response.json()) as TokenResponse;
  const idToken = new CognitoIdToken({ IdToken: tokens.id_token });
  const accessToken = new CognitoAccessToken({ AccessToken: tokens.access_token });
  const refreshToken = new CognitoRefreshToken({ RefreshToken: tokens.refresh_token });
  const session = new CognitoUserSession({
    IdToken: idToken,
    AccessToken: accessToken,
    RefreshToken: refreshToken,
  });
  const username = String(idToken.payload['cognito:username'] ?? idToken.payload.sub);
  const user = new CognitoUser({
    Username: username,
    Pool: new CognitoUserPool({ UserPoolId: USER_POOL_ID, ClientId: CLIENT_ID }),
  });
  user.setSignInUserSession(session);
  window.sessionStorage.removeItem(CODE_VERIFIER_KEY);
  window.sessionStorage.removeItem(OAUTH_STATE_KEY);
  return { token: tokens.id_token, user };
}

export function hostedUiLogoutUrl(origin: string): string {
  const logoutUrl = new URL(`${normalizeDomain(COGNITO_DOMAIN)}/logout`);
  logoutUrl.search = new URLSearchParams({
    client_id: CLIENT_ID,
    logout_uri: `${origin.replace(/\/$/, '')}/`,
  }).toString();
  return logoutUrl.toString();
}
