'use client';

import React from 'react';

// TODO: Wire to useCVList hook (spec-03)

export default function CVCenterPage() {
  return (
    <div className="flex flex-col gap-6">
      <h2 className="font-bold text-text-primary text-2xl">CV Center</h2>
      {/* TODO: CV upload and management UI */}
      <p className="text-text-muted">Manage your base CV here.</p>
    </div>
  );
}
