import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Unit tests for the Next.js /api/errors/ route handler, which forwards client
// error reports (server-to-server) to the backend API Gateway /errors endpoint.

const REPORT = {
  boundary_key: 'company-research-page',
  error: "Cannot read properties of undefined (reading 'length')",
  stack: 'TypeError: ...',
  user_agent: 'Mozilla/5.0',
  url: 'https://app.example.com/applications/abc/company-research/',
};

function makeRequest(body: unknown): Request {
  return new Request('http://localhost:3000/api/errors/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: typeof body === 'string' ? body : JSON.stringify(body),
  });
}

const ORIGINAL_API_URL = process.env.NEXT_PUBLIC_API_URL;

describe('/api/errors route handler', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com/prod';
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_URL = ORIGINAL_API_URL;
  });

  it('forwards the report to the backend /errors endpoint and returns 202', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(null, { status: 202 }));

    const { POST } = await import('../../app/api/errors/route');
    const res = await POST(makeRequest(REPORT));

    expect(res.status).toBe(202);
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    const [url, init] = fetchSpy.mock.calls[0];
    // Trailing slash on the base must not produce a double slash.
    expect(url).toBe('https://api.example.com/prod/errors');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toMatchObject({
      boundary_key: 'company-research-page',
    });
  });

  it('strips a trailing slash from the configured API base', async () => {
    process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com/prod/';
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(new Response(null, { status: 202 }));

    const { POST } = await import('../../app/api/errors/route');
    await POST(makeRequest(REPORT));

    expect(fetchSpy.mock.calls[0][0]).toBe('https://api.example.com/prod/errors');
  });

  it('still returns 202 when the backend forward fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { POST } = await import('../../app/api/errors/route');
    const res = await POST(makeRequest(REPORT));

    expect(res.status).toBe(202);
    expect(consoleSpy).toHaveBeenCalled();
  });

  it('does not call fetch and logs locally when no backend is configured', async () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { POST } = await import('../../app/api/errors/route');
    const res = await POST(makeRequest(REPORT));

    expect(res.status).toBe(202);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(consoleSpy).toHaveBeenCalled();
  });

  it('returns 202 without forwarding on a malformed JSON body', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    const { POST } = await import('../../app/api/errors/route');
    const res = await POST(makeRequest('{not json'));

    expect(res.status).toBe(202);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
