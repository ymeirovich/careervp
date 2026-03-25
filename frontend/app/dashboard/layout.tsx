"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/app/auth-context";
import { api } from "@/lib/api";
import { DashboardContext } from "@/app/dashboard/dashboard-context";
import { Sidebar } from "@/components/dashboard/Sidebar";
import type { Usage, SubscriptionResponse } from "@/lib/types";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [usage, setUsage] = useState<Usage | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(
    null
  );

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    if (!user) return;
    Promise.all([api.getUsage(), api.getSubscription()])
      .then(([usageData, subData]) => {
        setUsage(usageData);
        setSubscription(subData);
      })
      .catch(console.error);
  }, [user]);

  const userName = user?.name ?? user?.email?.split("@")[0] ?? "User";

  if (authLoading) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        style={{ backgroundColor: "#fcf7f5" }}
      >
        <span className="text-sm text-[#6b7280]">Loading…</span>
      </div>
    );
  }

  // Redirect in progress — render nothing while router.push("/login") fires
  if (!user) return null;

  return (
    <DashboardContext.Provider value={{ userName, usage, subscription }}>
      <div className="min-h-screen w-full" style={{ backgroundColor: "#fcf7f5" }}>
        <div
          className="mx-auto flex border border-[#cbd5e1] bg-[#fafafa]"
          style={{
            marginLeft: "100px",
            marginTop: "62px",
            width: "1239px",
            minHeight: "900px",
          }}
        >
          <Sidebar />
          <div className="flex flex-1 flex-col min-w-0">{children}</div>
        </div>
      </div>
    </DashboardContext.Provider>
  );
}
