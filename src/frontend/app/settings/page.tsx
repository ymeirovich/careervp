'use client';

import React, { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ErrorBoundary } from '../../components/ErrorBoundary/ErrorBoundary';
import { useUserContext } from '../../hooks/useUserContext';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../api/methods';

function SettingsContent() {
  const { user } = useUserContext();
  const { beginTotpEnrollment, changePassword, confirmTotpEnrollment } = useAuth();
  const queryClient = useQueryClient();

  const [displayName, setDisplayName] = useState(user?.name ?? '');
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState(false);

  // Sync displayName when user data loads/refreshes
  useEffect(() => {
    setDisplayName(user?.name ?? '');
  }, [user?.name]);

  const isProfileDirty = displayName.trim() !== (user?.name ?? '').trim();

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError(null);
    setProfileSuccess(false);
    setSavingProfile(true);
    try {
      await api.updateMe({ name: displayName.trim() });
      await queryClient.invalidateQueries({ queryKey: ['user', 'me'] });
      setProfileSuccess(true);
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : 'Failed to save profile.');
    } finally {
      setSavingProfile(false);
    }
  };

  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState(false);
  const [changingPw, setChangingPw] = useState(false);
  const [totpSecret, setTotpSecret] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [totpError, setTotpError] = useState<string | null>(null);
  const [totpSuccess, setTotpSuccess] = useState(false);
  const [configuringTotp, setConfiguringTotp] = useState(false);

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
    if (newPassword === oldPassword) {
      setPwError('New password must be different from current password.');
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

  const handleBeginTotp = async () => {
    setTotpError(null);
    setTotpSuccess(false);
    setConfiguringTotp(true);
    try {
      setTotpSecret(await beginTotpEnrollment());
    } catch (err) {
      setTotpError(err instanceof Error ? err.message : 'Failed to start authenticator setup.');
    } finally {
      setConfiguringTotp(false);
    }
  };

  const handleConfirmTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpError(null);
    setConfiguringTotp(true);
    try {
      await confirmTotpEnrollment(totpCode);
      setTotpSuccess(true);
      setTotpCode('');
      setTotpSecret('');
    } catch (err) {
      setTotpError(err instanceof Error ? err.message : 'Failed to verify authenticator code.');
    } finally {
      setConfiguringTotp(false);
    }
  };

  return (
    <div className="flex flex-col gap-8 max-w-xl" data-testid="settings-page">
      <h1 className="text-2xl font-bold text-text-primary">Settings</h1>

      {/* Profile section */}
      <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
        <h2 className="text-base font-bold text-text-primary">Profile</h2>
        <form onSubmit={(e) => void handleSaveProfile(e)} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => { setDisplayName(e.target.value); setProfileSuccess(false); }}
              className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-primary-action focus:ring-1 focus:ring-primary-action"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">Email</label>
            <input
              type="email"
              value={user?.email ?? ''}
              readOnly
              className="rounded border border-border-default px-3 py-2 text-sm text-text-muted bg-surface-subtle cursor-not-allowed"
            />
            <p className="text-xs text-text-muted">Email cannot be changed.</p>
          </div>
          {profileError && (
            <div className="rounded-md bg-state-error/10 border border-state-error px-3 py-2 text-sm text-state-error">{profileError}</div>
          )}
          {profileSuccess && (
            <div className="rounded-md bg-state-active/10 border border-state-active px-3 py-2 text-sm text-state-active">Profile saved.</div>
          )}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!isProfileDirty || savingProfile}
              className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {savingProfile ? 'Saving…' : 'Save Profile'}
            </button>
          </div>
        </form>
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
                  className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-primary-action focus:ring-1 focus:ring-primary-action"
                />
              </div>
            );
          })}
          {pwError && (
            <div className="rounded-md bg-state-error/10 border border-state-error px-3 py-2 text-sm text-state-error">{pwError}</div>
          )}
          {pwSuccess && (
            <div className="rounded-md bg-state-active/10 border border-state-active px-3 py-2 text-sm text-state-active">Password changed successfully.</div>
          )}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={changingPw}
              className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
            >
              {changingPw ? 'Changing…' : 'Change Password'}
            </button>
          </div>
        </form>
      </div>

      <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4" data-testid="totp-enrollment">
        <div>
          <h2 className="text-base font-bold text-text-primary">Authenticator app</h2>
          <p className="text-sm text-text-muted mt-1">
            Enroll during the MFA grace period so your account is ready before MFA becomes required.
          </p>
        </div>
        {!totpSecret && !totpSuccess && (
          <button
            type="button"
            onClick={() => void handleBeginTotp()}
            disabled={configuringTotp}
            className="self-start rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
          >
            {configuringTotp ? 'Starting…' : 'Set up authenticator'}
          </button>
        )}
        {totpSecret && (
          <form onSubmit={(e) => void handleConfirmTotp(e)} className="flex flex-col gap-3">
            <p className="text-sm text-text-primary">
              Enter this setup key in your authenticator app: <code className="font-mono break-all">{totpSecret}</code>
            </p>
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wide" htmlFor="totp-code">
              Six-digit verification code
            </label>
            <input
              id="totp-code"
              inputMode="numeric"
              pattern="[0-9]{6}"
              required
              value={totpCode}
              onChange={(e) => setTotpCode(e.currentTarget.value)}
              className="rounded border border-border-default px-3 py-2 text-sm text-text-primary bg-card focus:outline-none focus:border-primary-action focus:ring-1 focus:ring-primary-action"
            />
            <button
              type="submit"
              disabled={configuringTotp}
              className="self-start rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
            >
              {configuringTotp ? 'Verifying…' : 'Verify authenticator'}
            </button>
          </form>
        )}
        {totpError && <p className="text-sm text-state-error">{totpError}</p>}
        {totpSuccess && <p className="text-sm text-state-active">Authenticator app enabled.</p>}
      </div>

      {/* Placeholder sections */}
      {(['Notification Preferences', 'API Access'] as const).map((section) => (
        <div key={section} className="rounded-md border border-border-default bg-card p-6 flex items-center justify-between">
          <h2 className="text-base font-bold text-text-primary">{section}</h2>
          <span className="inline-flex px-2 py-0.5 rounded text-xs font-semibold bg-surface-subtle text-text-muted">Coming soon</span>
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
