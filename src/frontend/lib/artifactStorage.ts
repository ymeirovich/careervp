const KEY_PREFIX = 'cvp:artifacts';

function makeKey(jobId: string, moduleType: string): string {
  return `${KEY_PREFIX}:${jobId}:${moduleType}`;
}

export function persistArtifact(jobId: string, moduleType: string, taskId: string): void {
  try {
    localStorage.setItem(makeKey(jobId, moduleType), taskId);
  } catch (err) {
    console.warn('[artifactStorage] Failed to persist:', err);
  }
}

export function getArtifact(jobId: string, moduleType: string): string | null {
  try {
    return localStorage.getItem(makeKey(jobId, moduleType));
  } catch (err) {
    console.warn('[artifactStorage] Failed to get:', err);
    return null;
  }
}

export function clearArtifact(jobId: string, moduleType: string): void {
  try {
    localStorage.removeItem(makeKey(jobId, moduleType));
  } catch {
    // silent
  }
}

export function clearAllArtifacts(jobId: string): void {
  try {
    const prefix = `${KEY_PREFIX}:${jobId}:`;
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith(prefix)) keys.push(k);
    }
    keys.forEach((k) => localStorage.removeItem(k));
  } catch {
    // silent
  }
}
