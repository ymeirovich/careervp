import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { getCurrentToken } from '../lib/auth';

// Extend Axios config to support _retry flag for 401 retry-once pattern
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
  }
}

type ApiErrorPayload = {
  classification?: string;
  error?: string;
  error_code?: string;
  field?: string;
  message?: string;
};

export class ApiError extends Error {
  public readonly classification?: string;
  public readonly errorCode?: string;
  public readonly field?: string;
  public readonly isApiError = true;

  constructor(
    public readonly status: number,
    message: string,
    options?: {
      classification?: string;
      errorCode?: string;
      field?: string;
    },
  ) {
    super(message);
    this.name = 'ApiError';
    this.classification = options?.classification;
    this.errorCode = options?.errorCode;
    this.field = options?.field;
  }

  is404(): boolean {
    return this.status === 404;
  }

  get statusCode(): number {
    return this.status;
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
  async (error: AxiosError<ApiErrorPayload>) => {
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
    const payload = error.response?.data;
    const message = payload?.error ?? payload?.message ?? error.message;
    throw new ApiError(status, message, {
      classification: payload?.classification,
      errorCode: payload?.error_code,
      field: payload?.field,
    });
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
