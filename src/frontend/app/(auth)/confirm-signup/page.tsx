'use client';

import React, { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '../../../components/ui/Button';
import { useAuth } from '../../../contexts/AuthContext';

function ConfirmSignUpForm() {
  const { confirmSignUp } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams.get('email') ?? '';

  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await confirmSignUp(email, code);
      router.push('/login');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Verification failed. Please try again.';
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
          <h1 className="font-bold text-text-primary text-2xl">Verify your email</h1>
          {email && (
            <p className="text-text-muted text-sm mt-1">
              We sent a code to <span className="font-medium">{email}</span>
            </p>
          )}
        </div>

        {error && <p className="text-state-error text-sm text-center">{error}</p>}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="code" className="text-text-primary text-sm font-medium">
              Verification code
            </label>
            <input
              id="code"
              data-testid="code-input"
              type="text"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-base text-text-primary bg-card outline-none focus:ring-2 focus:ring-primary-action"
              placeholder="Enter 6-digit code"
            />
          </div>

          <Button
            data-testid="verify-button"
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            className="w-full mt-2"
          >
            Verify Email
          </Button>
        </form>

        <p className="text-center text-text-muted text-sm">
          Already verified?{' '}
          <a href="/login" className="text-primary-action hover:underline font-medium">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}

export default function ConfirmSignUpPage() {
  return (
    <Suspense>
      <ConfirmSignUpForm />
    </Suspense>
  );
}
