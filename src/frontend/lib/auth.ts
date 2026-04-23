import {
  CognitoUser,
  CognitoUserPool,
  AuthenticationDetails,
  CognitoUserAttribute,
  type CognitoUserSession,
} from 'amazon-cognito-identity-js';

const USER_POOL_ID =
  process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ?? 'us-east-1_WiHMRqLpe';
const CLIENT_ID =
  process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID ??
  process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ??
  '7blipbarsisbctqh6hlsj46sqa';

let _pool: CognitoUserPool | null = null;

function getPool(): CognitoUserPool {
  if (!_pool) {
    _pool = new CognitoUserPool({ UserPoolId: USER_POOL_ID, ClientId: CLIENT_ID });
  }
  return _pool;
}

/** Returns the idToken JWT. Throws Cognito error codes on failure. */
export function signIn(email: string, password: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: getPool() });
    const details = new AuthenticationDetails({ Username: email, Password: password });
    user.authenticateUser(details, {
      onSuccess(session: CognitoUserSession) {
        resolve(session.getIdToken().getJwtToken());
      },
      onFailure(err) {
        reject(err);
      },
    });
  });
}

export function signOut(): void {
  getPool().getCurrentUser()?.signOut();
}

export function signUp(email: string, password: string, name: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const attrs = [
      new CognitoUserAttribute({ Name: 'email', Value: email }),
      new CognitoUserAttribute({ Name: 'name', Value: name }),
    ];
    getPool().signUp(email, password, attrs, [], (err) => {
      if (err) { reject(err); return; }
      resolve();
    });
  });
}

export function confirmSignUp(email: string, code: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: getPool() });
    user.confirmRegistration(code, true, (err) => {
      if (err) { reject(err); return; }
      resolve();
    });
  });
}

export function resendConfirmationCode(email: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: getPool() });
    user.resendConfirmationCode((err) => {
      if (err) { reject(err); return; }
      resolve();
    });
  });
}

export function forgotPassword(email: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: getPool() });
    user.forgotPassword({
      onSuccess: () => resolve(),
      onFailure: (err) => reject(err),
    });
  });
}

export function confirmForgotPassword(
  email: string,
  code: string,
  newPassword: string,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: getPool() });
    user.confirmPassword(code, newPassword, {
      onSuccess: () => resolve(),
      onFailure: (err) => reject(err),
    });
  });
}

/**
 * Returns the current idToken if a valid Cognito session exists; null otherwise.
 * amazon-cognito-identity-js handles refresh automatically within getSession().
 */
export function getCurrentToken(): Promise<string | null> {
  return new Promise((resolve) => {
    const user = getPool().getCurrentUser();
    if (!user) { resolve(null); return; }
    user.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session?.isValid()) { resolve(null); return; }
      resolve(session.getIdToken().getJwtToken());
    });
  });
}

export function getCurrentCognitoUser(): CognitoUser | null {
  return getPool().getCurrentUser();
}
