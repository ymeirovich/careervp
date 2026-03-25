"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { CVForm } from "../_components/CVForm";
import type { UserCV } from "@/lib/types";

export default function CVEditPage() {
  const router = useRouter();
  const [cv, setCv] = useState<UserCV | null | undefined>(undefined); // undefined = loading

  useEffect(() => {
    api.getCV().then((data) => {
      if (!data) {
        // No CV yet — redirect to new
        router.replace("/dashboard/cv/new");
      } else {
        setCv(data);
      }
    });
  }, [router]);

  if (cv === undefined) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div className="text-sm text-[#6b7280]">Loading…</div>
      </div>
    );
  }

  return <CVForm initialCV={cv} isNew={false} />;
}
