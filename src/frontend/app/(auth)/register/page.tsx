'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '../../../components/ui/Button';
import { useAuth } from '../../../contexts/AuthContext';

export default function RegisterPage() {
  const { signUp } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await signUp(email, password);
      router.push(`/confirm-signup?email=${encodeURIComponent(email)}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed. Please try again.';
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
          <h1 className="font-bold text-text-primary text-2xl">Create your account</h1>
        </div>

        {error && (
          <p className="text-state-error text-sm text-center">{error}</p>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-text-primary text-sm font-medium">Email</label>
            <input
              id="email"
              data-testid="email-input"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-base text-text-primary bg-card outline-none focus:ring-2 focus:ring-primary-action"
              placeholder="you@example.com"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-text-primary text-sm font-medium">Password</label>
            <input
              id="password"
              data-testid="password-input"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-base text-text-primary bg-card outline-none focus:ring-2 focus:ring-primary-action"
              placeholder="Min. 8 characters"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="confirm-password" className="text-text-primary text-sm font-medium">
              Confirm password
            </label>
            <input
              id="confirm-password"
              data-testid="confirm-password-input"
              type="password"
              required
              minLength={8}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.currentTarget.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-base text-text-primary bg-card outline-none focus:ring-2 focus:ring-primary-action"
              placeholder="Repeat password"
            />
          </div>

          <Button
            data-testid="register-button"
            type="submit"
            variant="primary"
            size="lg"
            isLoading={loading}
            className="w-full mt-2"
          >
            Create Account
          </Button>
        </form>

        <p className="text-center text-text-muted text-sm">
          Already have an account?{' '}
          <a href="/login" className="text-primary-action hover:underline font-medium">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
