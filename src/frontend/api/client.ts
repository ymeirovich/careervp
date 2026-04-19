import axios, { type AxiosError } from 'axios';
import {
  CognitoUserPool,
  type CognitoUserSession,
} from 'amazon-cognito-identity-js';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const userPool = new CognitoUserPool({
  UserPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ?? '',
  ClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? '',
});

async function getIdToken(): Promise<string | null> {
  return new Promise((resolve) => {
    const user = userPool.getCurrentUser();
    if (!user) return resolve(null);
    user.getSession((err: Error | null, session: CognitoUserSession) => {
      if (err || !session?.isValid()) return resolve(null);
      resolve(session.getIdToken().getJwtToken());
    });
  });
}

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

apiClient.interceptors.request.use(async (config) => {
  const token = await getIdToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ code?: string; message?: string }>) => {
    if (error.response) {
      throw new ApiError(
        error.response.status,
        error.response.data?.code ?? 'UNKNOWN_ERROR',
        error.response.data?.message ?? error.message,
      );
    }
    throw error;
  },
);
