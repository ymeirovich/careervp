import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { getCurrentToken } from '../lib/auth';

// Extend Axios config to support _retry flag for 401 retry-once pattern
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  is404(): boolean {
    return this.status === 404;
  }
}

interface AuthContextHandle {
  refreshSession(): Promise<string>;
  signOut(): void;
}

let authContext: AuthContextHandle = {
  refreshSession: () => Promise.reject(new Error('AuthContext not initialised')),
  signOut: () => undefined,
};

export function setAuthContext(ctx: AuthContextHandle): void {
  authContext = ctx;
}

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  // Don't override Authorization if already set (e.g. by the 401 retry path)
  if (!config.headers.Authorization) {
    const token = await getCurrentToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ error?: string; message?: string }>) => {
    const originalRequest = error.config!;

    if (error.response?.status === 401) {
      if (!originalRequest._retry) {
        originalRequest._retry = true;
        try {
          const newToken = await authContext.refreshSession();
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        } catch {
          authContext.signOut();
          return Promise.reject(error);
        }
      }
      // Second 401 after retry — session is truly expired
      authContext.signOut();
    }

    const status = error.response?.status ?? 0;
    const message = error.response?.data?.error ?? error.message;
    throw new ApiError(status, message);
  },
);

export async function apiFetchOrNull<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn();
  } catch (err) {
    if (err instanceof ApiError && err.is404()) return null;
    throw err;
  }
}
