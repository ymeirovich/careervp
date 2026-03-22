export interface User {
  id: string;
  user_id: string;
  email: string;
  name?: string;
  preferences?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Usage {
  trial: {
    active: boolean;
    days_elapsed: number;
    days_remaining: number;
    ends_at: string;
  };
  applications: {
    used: number;
    remaining: number;
  };
}

export interface SubscriptionDetails {
  plan_type: "monthly" | "annual";
  status: "active" | "expired" | "canceled";
  current_period_end?: string;
}

export interface SubscriptionResponse {
  subscription: SubscriptionDetails | null;
  has_active_subscription: boolean;
}

export interface Job {
  id: string;
  job_id: string;
  title: string;
  company_name: string;
  status: string;
  created_at: string;
  url?: string;
  description?: string;
}

export interface CreateJobInput {
  title: string;
  company_name: string;
  description: string;
  url?: string;
  requirements?: string[];
}
