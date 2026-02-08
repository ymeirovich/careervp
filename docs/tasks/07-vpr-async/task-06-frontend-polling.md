# Task 7.6: Frontend Polling Component

**Status:** Not Started
**Spec Reference:** [[docs/specs/07-vpr-async-architecture.md]]
**Priority:** P0 (BLOCKING - Production VPR generation fails 100%)

## Overview

Create React component for VPR status polling. Frontend submits VPR job, receives `202 Accepted` with `job_id`, then polls `/api/vpr/status/{job_id}` every 5 seconds until status is `COMPLETED` or `FAILED`.

## Prerequisites

- [ ] Task 7.2 complete (submit endpoint returns 202 with job_id)
- [ ] Task 7.4 complete (status endpoint returns job status)
- [ ] React frontend codebase initialized
- [ ] Existing VPR submission form component

## Todo

### 1. Create VPRStatusPoller Component

**File:** `src/frontend/components/VPRStatusPoller.tsx`

- [ ] Create TypeScript React component
- [ ] Accept props: `jobId`, `onComplete`, `onError`, `onTimeout`
- [ ] Use `useEffect` hook for polling logic
- [ ] Poll every 5 seconds using `setTimeout`
- [ ] Maximum 60 polls (5 minutes timeout)
- [ ] Clean up interval on unmount

### 2. Implement Polling States

Track polling state with `useState`:

- [ ] `status`: `null | 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'`
- [ ] `pollingCount`: number (0-60)
- [ ] `resultUrl`: string | null
- [ ] `error`: string | null

### 3. Implement Status Check Logic

- [ ] Fetch `/api/vpr/status/{jobId}` every 5 seconds
- [ ] Handle HTTP status codes:
  - **202 Accepted**: Continue polling (PENDING/PROCESSING)
  - **200 OK**: Stop polling (COMPLETED or FAILED)
  - **404 Not Found**: Call `onError("Job not found")`
  - **410 Gone**: Call `onError("Result expired")`
  - **500 Error**: Call `onError("Server error")`
- [ ] Increment `pollingCount` after each poll
- [ ] If `pollingCount >= 60`, call `onTimeout()`

### 4. Handle Completion

- [ ] On `COMPLETED`:
  - Extract `result_url` from response
  - Call `onComplete(result_url)`
  - Stop polling
- [ ] On `FAILED`:
  - Extract `error` from response
  - Call `onError(error)`
  - Stop polling

### 5. Create UI Feedback Component

- [ ] Display status-specific messages:
  - PENDING: "🟡 VPR generation queued..."
  - PROCESSING: "🔵 Generating your personalized Value Proposition Report..."
  - COMPLETED: "✅ VPR complete! Loading results..."
  - FAILED: "❌ Unable to generate report. Please try again."
  - TIMEOUT: "⏱️ Generation is taking longer than expected. Please check back later."
- [ ] Show progress indicator (spinner or progress bar)
- [ ] Display elapsed time (optional)

### 6. Update VPR Submission Flow

**File:** `src/frontend/pages/VPRGenerationPage.tsx` (or similar)

- [ ] Update VPR submit handler to handle `202 Accepted`
- [ ] Extract `job_id` from submit response
- [ ] Render `VPRStatusPoller` component with job_id
- [ ] On `onComplete`, fetch VPR result from `result_url`
- [ ] Display VPR result to user
- [ ] On `onError`, show error message with retry option

### 7. Add Error Handling & Retry

- [ ] Implement retry mechanism for failed polls
- [ ] Maximum 3 retries per poll attempt
- [ ] Exponential backoff: 5s, 10s, 20s
- [ ] Show "Retry" button on permanent failure

### 8. Add Accessibility

- [ ] Add ARIA labels for screen readers
- [ ] Announce status changes to assistive technology
- [ ] Ensure keyboard navigation works
- [ ] Add loading states for better UX

## Codex Implementation Guide

### Implementation: VPRStatusPoller.tsx

```typescript
/**
 * VPRStatusPoller Component
 *
 * Polls VPR job status until completion or failure.
 * Displays status-specific UI feedback.
 */

import { useState, useEffect } from 'react';

interface VPRStatus {
  job_id: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  result_url?: string;
  error?: string;
  token_usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

interface VPRStatusPollerProps {
  jobId: string;
  onComplete: (resultUrl: string) => void;
  onError: (error: string) => void;
  onTimeout?: () => void;
  pollingInterval?: number;  // Default: 5000ms
  maxPolls?: number;  // Default: 60 (5 minutes)
}

export function VPRStatusPoller({
  jobId,
  onComplete,
  onError,
  onTimeout,
  pollingInterval = 5000,
  maxPolls = 60
}: VPRStatusPollerProps) {
  const [status, setStatus] = useState<VPRStatus | null>(null);
  const [pollingCount, setPollingCount] = useState(0);
  const [isPolling, setIsPolling] = useState(true);

  useEffect(() => {
    if (!isPolling) return;

    const pollStatus = async () => {
      // Check timeout
      if (pollingCount >= maxPolls) {
        setIsPolling(false);
        onTimeout?.();
        onError('VPR generation timeout. Please try again.');
        return;
      }

      try {
        const response = await fetch(`/api/vpr/status/${jobId}`);

        // Handle different HTTP status codes
        if (response.status === 404) {
          setIsPolling(false);
          onError('Job not found (may have expired)');
          return;
        }

        if (response.status === 410) {
          setIsPolling(false);
          onError('Result expired. Please regenerate VPR.');
          return;
        }

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: VPRStatus = await response.json();
        setStatus(data);

        // Handle completion states
        if (data.status === 'COMPLETED') {
          setIsPolling(false);
          if (data.result_url) {
            onComplete(data.result_url);
          } else {
            onError('Result URL missing from completed job');
          }
        } else if (data.status === 'FAILED') {
          setIsPolling(false);
          onError(data.error || 'VPR generation failed');
        } else {
          // Still processing, continue polling
          setPollingCount(prev => prev + 1);
          setTimeout(pollStatus, pollingInterval);
        }
      } catch (error) {
        console.error('Error polling VPR status:', error);
        setPollingCount(prev => prev + 1);
        // Retry on next interval
        setTimeout(pollStatus, pollingInterval);
      }
    };

    // Start polling
    pollStatus();

    // Cleanup on unmount
    return () => {
      setIsPolling(false);
    };
  }, [jobId, pollingCount, isPolling, maxPolls, pollingInterval, onComplete, onError, onTimeout]);

  // Calculate elapsed time
  const elapsedSeconds = pollingCount * (pollingInterval / 1000);
  const elapsedMinutes = Math.floor(elapsedSeconds / 60);
  const remainingSeconds = elapsedSeconds % 60;

  return (
    <div className="vpr-status-poller" role="status" aria-live="polite">
      {/* Status Icon */}
      <div className="status-icon">
        {status?.status === 'PENDING' && '🟡'}
        {status?.status === 'PROCESSING' && '🔵'}
        {status?.status === 'COMPLETED' && '✅'}
        {status?.status === 'FAILED' && '❌'}
        {!status && '⏳'}
      </div>

      {/* Status Message */}
      <div className="status-message">
        {status?.status === 'PENDING' && (
          <p>VPR generation queued...</p>
        )}
        {status?.status === 'PROCESSING' && (
          <p>Generating your personalized Value Proposition Report...</p>
        )}
        {status?.status === 'COMPLETED' && (
          <p>VPR complete! Loading results...</p>
        )}
        {status?.status === 'FAILED' && (
          <p>Unable to generate report. Please try again.</p>
        )}
        {!status && (
          <p>Checking status...</p>
        )}
      </div>

      {/* Progress Indicator */}
      <div className="progress-indicator">
        <div className="spinner" />
        <p className="elapsed-time">
          Elapsed: {elapsedMinutes}:{remainingSeconds.toString().padStart(2, '0')}
        </p>
      </div>

      {/* Debug Info (dev only) */}
      {process.env.NODE_ENV === 'development' && status && (
        <details className="debug-info">
          <summary>Debug Info</summary>
          <pre>{JSON.stringify(status, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}
```

### Updated VPR Submission Flow

```typescript
// src/frontend/pages/VPRGenerationPage.tsx

import { useState } from 'react';
import { VPRStatusPoller } from '../components/VPRStatusPoller';

export function VPRGenerationPage() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [vprResult, setVprResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (vprRequest: VPRRequest) => {
    try {
      const response = await fetch('/api/vpr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(vprRequest)
      });

      if (response.status === 202) {
        // Async job submitted
        const data = await response.json();
        setJobId(data.job_id);
      } else if (response.status === 200) {
        // Idempotent request (job already exists)
        const data = await response.json();
        setJobId(data.job_id);
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleComplete = async (resultUrl: string) => {
    try {
      // Fetch VPR result from presigned S3 URL
      const response = await fetch(resultUrl);
      const vpr = await response.json();
      setVprResult(vpr);
    } catch (err) {
      setError('Failed to fetch VPR result');
    }
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const handleRetry = () => {
    setJobId(null);
    setError(null);
    setVprResult(null);
  };

  return (
    <div className="vpr-generation-page">
      <h1>Generate Value Proposition Report</h1>

      {/* VPR Request Form */}
      {!jobId && !vprResult && (
        <VPRRequestForm onSubmit={handleSubmit} />
      )}

      {/* Status Polling */}
      {jobId && !vprResult && !error && (
        <VPRStatusPoller
          jobId={jobId}
          onComplete={handleComplete}
          onError={handleError}
        />
      )}

      {/* VPR Result Display */}
      {vprResult && (
        <VPRResultView vpr={vprResult} />
      )}

      {/* Error Display */}
      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button onClick={handleRetry}>Retry</button>
        </div>
      )}
    </div>
  );
}
```

### CSS Styling (Optional)

```css
/* VPRStatusPoller.css */

.vpr-status-poller {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  background: #f9fafb;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.status-icon {
  font-size: 3rem;
}

.status-message {
  text-align: center;
  font-size: 1.125rem;
  color: #374151;
}

.progress-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.elapsed-time {
  font-size: 0.875rem;
  color: #6b7280;
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  color: #991b1b;
}
```

## Verification Commands

### Local Development Testing

```bash
# 1. Start frontend dev server
cd src/frontend
npm run dev

# 2. Open browser to http://localhost:3000
# 3. Submit VPR request
# 4. Observe polling behavior in browser DevTools Network tab
# 5. Verify status updates every 5 seconds
# 6. Verify completion after ~60 seconds
```

### Integration Testing

```bash
# Test complete flow
# 1. Submit VPR request
# 2. See "VPR generation queued..." (PENDING)
# 3. See "Generating..." (PROCESSING)
# 4. Wait 30-60 seconds
# 5. See "VPR complete!" (COMPLETED)
# 6. VPR result displays

# Test timeout
# 1. Manually delay worker Lambda (increase timeout to >5 minutes)
# 2. Submit VPR request
# 3. Wait 5 minutes
# 4. See timeout error message

# Test failure
# 1. Submit invalid VPR request (trigger worker failure)
# 2. See "Unable to generate report" (FAILED)
# 3. Click Retry button
# 4. Form resets
```

## Acceptance Criteria

- [ ] VPRStatusPoller component created
- [ ] Polls every 5 seconds until completion
- [ ] Maximum 60 polls (5-minute timeout)
- [ ] Displays status-specific UI feedback
- [ ] Handles COMPLETED status (fetches result from presigned URL)
- [ ] Handles FAILED status (shows error message)
- [ ] Handles timeout (shows timeout message)
- [ ] Handles 404/410 HTTP errors gracefully
- [ ] Cleanup interval on component unmount
- [ ] Accessible (ARIA labels, keyboard navigation)
- [ ] Works in all major browsers (Chrome, Firefox, Safari, Edge)

## Dependencies

**Blocks:**
- None (frontend is final integration layer)

**Blocked By:**
- Task 7.2 (Submit Handler) - needs 202 response with job_id
- Task 7.4 (Status Handler) - needs status endpoint

## Estimated Effort

**Time:** 4-6 hours
**Complexity:** MEDIUM (React hooks + polling logic + error handling)

## Notes

- Polling interval: 5 seconds (configurable prop)
- Max polls: 60 (5 minutes total, configurable prop)
- Presigned S3 URL expires in 1 hour (fetch result immediately)
- Consider adding exponential backoff for failed polls
- Consider adding visual progress bar (optional enhancement)
- Test on slow network connections (throttle in DevTools)
