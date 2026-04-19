type ModuleType = string;

interface ModuleTimingEvent {
  event: 'module_generation_completed';
  module_type: ModuleType;
  duration_ms: number;
  poll_count: number;
  quality_score?: number;
}

interface ModuleErrorEvent {
  event: 'module_generation_failed';
  module_type: ModuleType;
  error_code: string;
  duration_ms: number;
}

type InstrumentationEvent = ModuleTimingEvent | ModuleErrorEvent;

const startTimes = new Map<string, number>();
const pollCounts = new Map<string, number>();

function sessionKey(moduleType: ModuleType, jobId: string): string {
  return `${moduleType}:${jobId}`;
}

export function recordGenerationStart(moduleType: ModuleType, jobId: string): void {
  const key = sessionKey(moduleType, jobId);
  startTimes.set(key, performance.now());
  pollCounts.set(key, 0);
}

export function recordPoll(moduleType: ModuleType, jobId: string): void {
  const key = sessionKey(moduleType, jobId);
  pollCounts.set(key, (pollCounts.get(key) ?? 0) + 1);
}

export function recordGenerationComplete(
  moduleType: ModuleType,
  jobId: string,
  qualityScore?: number,
): void {
  const key = sessionKey(moduleType, jobId);
  const startMs = startTimes.get(key);
  if (startMs === undefined) return;

  const duration_ms = Math.round(performance.now() - startMs);
  const poll_count = pollCounts.get(key) ?? 0;

  emit({ event: 'module_generation_completed', module_type: moduleType, duration_ms, poll_count, quality_score: qualityScore });
  startTimes.delete(key);
  pollCounts.delete(key);
}

export function recordGenerationFailed(
  moduleType: ModuleType,
  jobId: string,
  errorCode: string,
): void {
  const key = sessionKey(moduleType, jobId);
  const startMs = startTimes.get(key);
  const duration_ms = startMs !== undefined ? Math.round(performance.now() - startMs) : 0;

  emit({ event: 'module_generation_failed', module_type: moduleType, error_code: errorCode, duration_ms });
  startTimes.delete(key);
  pollCounts.delete(key);
}

function emit(payload: InstrumentationEvent): void {
  // AWS RUM picks this up automatically when the RUM snippet is injected.
  // Fallback: POST to /metrics if RUM is not configured.
  try {
    const rum = (window as any).cwr;
    if (typeof rum === 'function') {
      rum('recordEvent', payload.event, payload);
      return;
    }
  } catch {
    // RUM not available
  }

  const metricsUrl = process.env.NEXT_PUBLIC_METRICS_ENDPOINT;
  if (metricsUrl) {
    navigator.sendBeacon(metricsUrl, JSON.stringify(payload));
  }
}
