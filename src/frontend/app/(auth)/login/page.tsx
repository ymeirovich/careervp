'use client';

import React, { useState } from 'react';
import { Button } from '../../../components/ui/Button';

// TODO: Wire to AuthContext signIn() (spec-06)
// Cognito User Pool: us-east-1_WiHMRqLpe | Client: 7blipbarsisbctqh6hlsja46sqa

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // TODO: await signIn(email, password);
      // TODO: router.push('/dashboard');
      console.log('Sign in', email);
    } catch {
      setError('Invalid email or password.');
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
          <h1 className="font-bold text-text-primary text-2xl">Sign in to CareerVP</h1>
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
              onChange={(e) => setEmail(e.target.value)}
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="border border-border-default rounded-lg px-3 py-2 text-base text-text-primary bg-card outline-none focus:ring-2 focus:ring-primary-action"
              placeholder="••••••••"
            />
          </div>

          <Button
            data-testid="sign-in-button"
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            className="w-full mt-2"
          >
            Sign In
          </Button>
        </form>

        <p className="text-center text-text-muted text-sm">
          Don&apos;t have an account?{' '}
          <a href="/register" className="text-primary-action hover:underline font-medium">
            Register
          </a>
        </p>
      </div>
    </div>
  );
}
