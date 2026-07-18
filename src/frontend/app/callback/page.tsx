'use client';

import { useEffect, useState } from 'react';
import { completePkceSignIn } from '../../lib/pkce';

export default function AuthCallbackPage() {
  const [error, setError] = useState('');

  useEffect(() => {
    completePkceSignIn()
      .then(() => window.location.replace('/dashboard'))
      .catch(() => setError('Sign in could not be completed. Please return to the login page.'));
  }, []);

  return (
    <main className="min-h-screen bg-page-bg flex items-center justify-center">
      <div className="bg-card border border-border-default rounded-xl p-8 w-full max-w-sm text-center">
        {error ? (
          <>
            <p className="text-state-error text-sm">{error}</p>
            <a href="/login" className="text-primary-action hover:underline text-sm">
              Return to login
            </a>
          </>
        ) : (
          <p className="text-text-muted text-sm">Completing secure sign in…</p>
        )}
      </div>
    </main>
  );
}
