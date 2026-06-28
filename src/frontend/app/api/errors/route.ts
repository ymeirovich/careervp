import { NextResponse } from 'next/server';

// Receives client-side error reports from ErrorBoundary.logToCloudWatch and
// forwards them (server-to-server) to the backend API Gateway `/errors`
// endpoint, where a Powertools-logging Lambda lands them in backend CloudWatch
// alongside the rest of the structured backend logs.
//
// Kept deliberately tolerant: a telemetry endpoint must never throw back at the
// browser, which is already fire-and-forget. If the backend forward fails we
// fall back to logging in the Amplify SSR function's own log group.

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

interface ClientErrorReport {
  error?: string;
  stack?: string;
  boundary_key?: string;
  user_agent?: string;
  url?: string;
}

export async function POST(request: Request): Promise<NextResponse> {
  let report: ClientErrorReport = {};
  try {
    report = (await request.json()) as ClientErrorReport;
  } catch {
    // Malformed/empty body — still ack so the client doesn't retry-loop.
    return NextResponse.json({ ok: false, reason: 'invalid_json' }, { status: 202 });
  }

  const apiBase = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  if (apiBase) {
    try {
      await fetch(`${apiBase}/errors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(report),
        // Don't let a slow backend hang the request; reports are best-effort.
        signal: AbortSignal.timeout(3000),
      });
    } catch {
      // Backend unreachable/slow — fall back to the SSR function's log group.
      console.error('[client-error] backend forward failed', {
        boundary_key: report.boundary_key ?? 'unknown',
        error: report.error ?? '',
        url: report.url ?? '',
      });
    }
  } else {
    // No backend configured (e.g. local dev) — log locally so reports aren't lost.
    console.error('[client-error]', {
      boundary_key: report.boundary_key ?? 'unknown',
      error: report.error ?? '',
      url: report.url ?? '',
      user_agent: report.user_agent ?? '',
      stack: report.stack ?? '',
    });
  }

  return NextResponse.json({ ok: true }, { status: 202 });
}
