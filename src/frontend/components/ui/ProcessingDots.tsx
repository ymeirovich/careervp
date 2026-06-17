'use client';

import { useEffect, useState } from 'react';

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
}

export function ProcessingDots() {
  const [reducedMotion, setReducedMotion] = useState(prefersReducedMotion);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  if (reducedMotion) {
    return <span>Processing...</span>;
  }

  return (
    <span>
      Processing
      <span aria-hidden="true" className="animate-dot-1">.</span>
      <span aria-hidden="true" className="animate-dot-2">.</span>
      <span aria-hidden="true" className="animate-dot-3">.</span>
    </span>
  );
}
