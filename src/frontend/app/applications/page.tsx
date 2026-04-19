'use client';

import React from 'react';

// TODO: Wire to useApplicationsList hook (spec-03)

export default function ApplicationsPage() {
  return (
    <div className="flex flex-col gap-6">
      <h2 className="font-bold text-text-primary text-2xl">All Applications</h2>
      {/* TODO: Render full applications list with JobsTable */}
      <p className="text-text-muted">Loading applications…</p>
    </div>
  );
}
