'use client';

import React from 'react';

// TODO: Wire to useUserProfile hook (spec-03)

export default function SettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <h2 className="font-bold text-text-primary text-2xl">Settings</h2>
      {/* TODO: Profile settings, notification preferences, language selection */}
      <p className="text-text-muted">Account settings and preferences.</p>
    </div>
  );
}
