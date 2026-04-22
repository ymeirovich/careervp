import figma from '@figma/code-connect';
import { ModuleCard } from './ModuleCard';

figma.connect(ModuleCard, 'REPLACE_WITH_FIGMA_NODE_URL_FOR_MODULE_CARD', {
  props: {
    state: figma.enum('State', {
      'Not Started': 'notStarted',
      Processing: 'processing',
      Ready: 'ready',
      Complete: 'complete',
      Edited: 'edited',
      Stale: 'stale',
      Failed: 'failed',
      Timeout: 'timeout',
      Final: 'final',
    }),
    module: figma.enum('Module', {
      VPR: 'vpr',
      CV: 'tailoredCV',
      'Cover Letter': 'coverLetter',
      'Interview Prep': 'interviewPrep',
      'Gap Analysis': 'gapAnalysis',
      'Company Research': 'companyResearch',
      'Base CV': 'baseCV',
    }),
  },
  example: ({ state, module }) => (
    <ModuleCard state={state} module={module} title="" />
  ),
});
