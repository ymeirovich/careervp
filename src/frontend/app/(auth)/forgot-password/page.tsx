'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '../../../components/ui/Button';
import { useAuth } from '../../../contexts/AuthContext';

export default function ForgotPasswordPage() {
  const { forgotPassword } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await forgotPassword(email);
      router.push(`/reset-password?email=${encodeURIComponent(email)}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send reset code. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-page-bg flex items-center justify-center">
      <div className="bg-card border border-border-default rounded-xl p-8 w-full max-w-sm flex flex-col gap-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 bg-primary-action rounded-md mb-4">
            <span className="text-white font-bold text-sm">CV</span>
          </div>
          <h1 className="font-bold text-text-primary text-2xl">Reset your password</h1>
          <p className="text-text-muted text-sm mt-1">
            Enter your email and we&apos;ll send a reset code.
          </p>
        </div>

        {error && <p className="text-state-error text-sm text-center">{error}</p>}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-text-primary text-sm font-medium">Email</label>
            <input
              id="email"
              data-testid="email-input"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-base text-text-primary bg-card outline-none focus:ring-2 focus:ring-primary-action"
              placeholder="you@example.com"
            />
          </div>

          <Button
            data-testid="send-code-button"
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            className="w-full mt-2"
          >
            Send Reset Code
          </Button>
        </form>

        <p className="text-center text-text-muted text-sm">
          Remembered it?{' '}
          <a href="/login" className="text-primary-action hover:underline font-medium">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
