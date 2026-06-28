import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

const apiMocks = vi.hoisted(() => ({
  generateCoverLetter: vi.fn(),
  generateVPR: vi.fn(),
  generateInterviewPrep: vi.fn(),
  generateCV: vi.fn(),
  cancelVpr: vi.fn(),
  cancelCoverLetter: vi.fn(),
  cancelInterviewPrep: vi.fn(),
  cancelCvTailoring: vi.fn(),
}));

vi.mock('../../api/methods', () => ({ api: apiMocks }));
vi.mock('../../lib/artifactStorage', () => ({
  persistArtifact: vi.fn(),
  clearArtifact: vi.fn(),
  getArtifact: vi.fn().mockReturnValue(null),
}));

import { useGenerateModule } from '../../hooks/useGenerateModule';

const JOB_ID = 'job-test-001';

describe('useGenerateModule — cover letter: company_research_id', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.generateCoverLetter.mockResolvedValue({ request_id: 'req-1' });
  });

  it('omits company_research_id (undefined) when companyResearchId not provided', async () => {
    const { result } = renderHook(() => useGenerateModule('coverLetter', JOB_ID));

    await act(async () => {
      await result.current.generate({
        cvId: 'cv-1',
        vprId: 'vpr-1',
        gapResponseIds: ['r1'],
      });
    });

    expect(apiMocks.generateCoverLetter).toHaveBeenCalledOnce();
    const callArg = apiMocks.generateCoverLetter.mock.calls[0][0] as Record<string, unknown>;
    expect(callArg.company_research_id).toBeUndefined();
  });

  it('passes company_research_id when companyResearchId is provided', async () => {
    const { result } = renderHook(() => useGenerateModule('coverLetter', JOB_ID));

    await act(async () => {
      await result.current.generate({
        cvId: 'cv-1',
        vprId: 'vpr-1',
        gapResponseIds: ['r1'],
        companyResearchId: 'cr-abc',
      });
    });

    expect(apiMocks.generateCoverLetter).toHaveBeenCalledOnce();
    const callArg = apiMocks.generateCoverLetter.mock.calls[0][0] as Record<string, unknown>;
    expect(callArg.company_research_id).toBe('cr-abc');
  });

  it('does not pass empty string for company_research_id', async () => {
    const { result } = renderHook(() => useGenerateModule('coverLetter', JOB_ID));

    await act(async () => {
      await result.current.generate({
        cvId: 'cv-1',
        vprId: 'vpr-1',
        gapResponseIds: ['r1'],
        // companyResearchId intentionally absent
      });
    });

    const callArg = apiMocks.generateCoverLetter.mock.calls[0][0] as Record<string, unknown>;
    expect(callArg.company_research_id).not.toBe('');
  });
});
