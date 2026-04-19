export const queryKeys = {
  applications: {
    list: () => ['applications'] as const,
    detail: (applicationId: string) => ['applications', applicationId] as const,
  },
  vpr: {
    status: (jobId: string) => ['vpr', 'status', jobId] as const,
  },
  coverLetter: {
    status: (jobId: string) => ['coverLetter', 'status', jobId] as const,
  },
  interviewPrep: {
    status: (jobId: string) => ['interviewPrep', 'status', jobId] as const,
  },
  cvTailoring: {
    status: (jobId: string) => ['cvTailoring', 'status', jobId] as const,
  },
  gapAnalysis: {
    detail: (jobId: string) => ['gapAnalysis', jobId] as const,
  },
  companyResearch: {
    detail: (companyName: string) => ['companyResearch', companyName] as const,
  },
  cv: {
    detail: () => ['cv', 'me'] as const,
  },
  user: {
    me: () => ['user', 'me'] as const,
  },
} as const;
