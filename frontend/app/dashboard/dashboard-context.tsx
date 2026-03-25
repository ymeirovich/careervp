"use client";

import { createContext, useContext } from "react";
import type { Usage, SubscriptionResponse } from "@/lib/types";

interface DashboardContextValue {
  userName: string;
  usage: Usage | null;
  subscription: SubscriptionResponse | null;
}

export const DashboardContext = createContext<DashboardContextValue>({
  userName: "",
  usage: null,
  subscription: null,
});

export function useDashboard(): DashboardContextValue {
  return useContext(DashboardContext);
}
