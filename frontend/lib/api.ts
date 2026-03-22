import { getCurrentToken } from "./auth";
import type {
  User,
  Usage,
  SubscriptionResponse,
  Job,
  CreateJobInput,
} from "./types";

// Route through the Next.js proxy to avoid CORS preflight issues with API Gateway.
const API_BASE = "/api/proxy";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getCurrentToken();

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  getMe: () => apiFetch<User>("/users/me"),
  getUsage: () => apiFetch<Usage>("/users/me/usage"),
  getSubscription: () =>
    apiFetch<SubscriptionResponse>("/users/me/subscription"),
  getJobs: async (): Promise<Job[]> => {
    const data = await apiFetch<{ jobs: Job[] }>("/jobs");
    return data.jobs ?? [];
  },
  createJob: (data: CreateJobInput) =>
    apiFetch<Job>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
