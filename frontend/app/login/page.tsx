"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/app/auth-context";

export default function LoginPage() {
  const { signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signIn(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{ backgroundColor: "#fcf7f5" }}
    >
      <div className="w-full max-w-md rounded-[8px] border border-[#cbd5e1] bg-white p-8 shadow-sm">
        {/* Logo */}
        <div className="mb-6 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-[4px] bg-[#f97316]">
            <span className="text-xs font-bold text-white">CVP</span>
          </div>
          <span className="text-lg font-bold text-[#1e2229]">CareerVP</span>
        </div>

        <h1 className="mb-6 text-2xl font-semibold text-[#1e2229]">Sign in</h1>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-[#1e2229]">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter email"
              required
              className="rounded-[4px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] outline-none focus:border-[#f97316] transition-colors"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-[#1e2229]">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              className="rounded-[4px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229] outline-none focus:border-[#f97316] transition-colors"
            />
          </div>

          {error && (
            <p className="rounded-[4px] bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 rounded-[8px] bg-[#f97316] px-4 py-2.5 text-sm font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
