'use client';

import React, { useState } from 'react';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { useUserContext } from '../../hooks/useUserContext';
import { useAuth } from '../../contexts/AuthContext';

function SettingsContent() {
  const { user } = useUserContext();
  const { changePassword } = useAuth();

  const [displayName, setDisplayName] = useState(user?.name ?? '');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState(false);
  const [changingPw, setChangingPw] = useState(false);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError(null);
    setPwSuccess(false);

    if (newPassword !== confirmPassword) {
      setPwError('New passwords do not match.');
      return;
    }
    if (newPassword.length < 8) {
      setPwError('Password must be at least 8 characters.');
      return;
    }

    setChangingPw(true);
    try {
      await changePassword(oldPassword, newPassword);
      setPwSuccess(true);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPwError(err instanceof Error ? err.message : 'Failed to change password.');
    } finally {
      setChangingPw(false);
    }
  };

  return (
    <div className="flex flex-col gap-8 max-w-xl" data-testid="settings-page">
      <h1 className="text-2xl font-bold text-text-primary">Settings</h1>

      {/* Profile section */}
      <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
        <h2 className="text-base font-bold text-text-primary">Profile</h2>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Email</label>
            <input
              type="email"
              value={user?.email ?? ''}
              readOnly
              className="rounded border border-border-default px-3 py-2 text-sm text-text-muted bg-bg-subtle cursor-not-allowed"
            />
            <p className="text-xs text-text-muted">Email cannot be changed.</p>
          </div>
          <div className="flex justify-end">
            <button
              disabled
              className="rounded-md bg-brand-primary px-3 py-2 text-sm font-bold text-white opacity-50 cursor-not-allowed"
              title="Save profile — coming soon"
            >
              Save Profile
            </button>
          </div>
        </div>
      </div>

      {/* Security section */}
      <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4" data-testid="change-password-form">
        <h2 className="text-base font-bold text-text-primary">Security</h2>
        <form onSubmit={(e) => void handleChangePassword(e)} className="flex flex-col gap-3">
          {(['Current Password', 'New Password', 'Confirm New Password'] as const).map((label, i) => {
            const values = [oldPassword, newPassword, confirmPassword];
            const setters = [setOldPassword, setNewPassword, setConfirmPassword];
            return (
              <div key={label} className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">{label}</label>
                <input
                  type="password"
                  value={values[i]}
                  onChange={(e) => setters[i](e.target.value)}
                  required
                  className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
                />
              </div>
            );
          })}
          {pwError && (
            <div className="rounded-md bg-state-error/10 border border-state-error px-3 py-2 text-sm text-state-error">{pwError}</div>
          )}
          {pwSuccess && (
            <div className="rounded-md bg-state-success/10 border border-state-success px-3 py-2 text-sm text-state-success">Password changed successfully.</div>
          )}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={changingPw}
              className="rounded-md bg-brand-primary px-3 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
            >
              {changingPw ? 'Changing…' : 'Change Password'}
            </button>
          </div>
        </form>
      </div>

      {/* Placeholder sections */}
      {(['Notification Preferences', 'API Access'] as const).map((section) => (
        <div key={section} className="rounded-md border border-border-default bg-card p-6 flex items-center justify-between">
          <h2 className="text-base font-bold text-text-primary">{section}</h2>
          <span className="inline-flex px-2 py-0.5 rounded text-xs font-semibold bg-bg-subtle text-text-muted">Coming soon</span>
        </div>
      ))}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ErrorBoundary cloudwatchKey="settings-page">
      <SettingsContent />
    </ErrorBoundary>
  );
}
