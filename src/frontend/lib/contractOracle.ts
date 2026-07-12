import fs from 'node:fs';
import path from 'node:path';
import Ajv2020 from 'ajv/dist/2020';
import type { AnySchema } from 'ajv';
import type { ValidateFunction } from 'ajv';
import {
  artifactStatusValues,
  contractSchemas,
  flatErrorEnvelopeSchema,
} from './contractSchemas';
import type { ApplicationHubData, AsyncTaskResponse, ExportResponse, HubArtifact, InterviewPrepPatchResponse, VPRStatusResponse } from './types';

export const backendSchemaNames = [
  'ApplicationHubData',
  'AsyncTaskResponse',
  'CompanyResearchResult',
  'CoverLetterStatusResponse',
  'CVTailoredStatusResponse',
  'CVTailoringRequest',
  'ErrorResponse',
  'ExportResponse',
  'InterviewPrepPatchResponse',
  'InterviewPrepStatusResponse',
  'VPRStatusResponse',
] as const;

export type BackendSchemaName = (typeof backendSchemaNames)[number];
type ArtifactStatus = (typeof artifactStatusValues)[number];
type StatusEndpointFixtures = Partial<Record<keyof ApplicationHubData['artifacts'], { id?: string; status?: string } | null>>;

const ajv = new Ajv2020({ allErrors: true, strict: false, validateFormats: false });
const backendValidators = new Map<BackendSchemaName, ValidateFunction>();

function schemaDir(): string {
  const fromSourceDir = path.resolve(__dirname, '../../backend/contract/schemas');
  if (fs.existsSync(fromSourceDir)) return fromSourceDir;
  return path.resolve(process.cwd(), '../backend/contract/schemas');
}

function loadBackendSchema(schemaName: BackendSchemaName): unknown {
  const schemaPath = path.join(schemaDir(), `${schemaName}.json`);
  return JSON.parse(fs.readFileSync(schemaPath, 'utf-8')) as unknown;
}

function backendValidator(schemaName: BackendSchemaName): ValidateFunction {
  const cached = backendValidators.get(schemaName);
  if (cached) return cached;
  const compiled = ajv.compile(loadBackendSchema(schemaName) as AnySchema);
  backendValidators.set(schemaName, compiled);
  return compiled;
}

function formatAjvErrors(validate: ValidateFunction): string {
  return (validate.errors ?? [])
    .map((error) => `${error.instancePath || '/'} ${error.message ?? 'failed validation'}`)
    .join('; ');
}

export function validateBothTruths(schemaName: BackendSchemaName | string, payload: unknown): void {
  if (!backendSchemaNames.includes(schemaName as BackendSchemaName)) {
    throw new Error(`unknown contract schema: ${schemaName}`);
  }
  const name = schemaName as BackendSchemaName;
  const zodResult = contractSchemas[name].safeParse(payload);
  if (!zodResult.success) {
    throw new Error(`${name} failed FE Zod truth: ${zodResult.error.issues.map((issue) => issue.path.join('.') || issue.message).join(', ')}`);
  }
  const validate = backendValidator(name);
  if (!validate(payload)) {
    throw new Error(`${name} failed BE Pydantic/ajv truth: ${formatAjvErrors(validate)}`);
  }
}

export function assertApplicationIdsMatch(hub: ApplicationHubData): void {
  if (hub.application.application_id !== hub.job.job_id) {
    throw new Error(`application_id must equal job_id: ${hub.application.application_id} !== ${hub.job.job_id}`);
  }
}

export function assertArtifactRoundTrip(hub: ApplicationHubData, statuses: StatusEndpointFixtures): void {
  for (const [artifactType, hubArtifact] of Object.entries(hub.artifacts) as Array<[keyof ApplicationHubData['artifacts'], HubArtifact]>) {
    if (hubArtifact.artifact_id === null) continue;
    const statusFixture = statuses[artifactType];
    if (!statusFixture || statusFixture.id !== hubArtifact.artifact_id) {
      throw new Error(`${String(artifactType)} artifact_id did not round-trip to status endpoint`);
    }
  }
}

export function assertVprIdContract(hub: ApplicationHubData, request: unknown, nonNullRequest: { vpr_id?: string | null }): void {
  if (!request || typeof request !== 'object' || !Object.prototype.hasOwnProperty.call(request, 'vpr_id')) {
    throw new Error('vpr_id absent; null-vs-absent is load-bearing');
  }
  const vprId = (request as { vpr_id?: unknown }).vpr_id;
  if (vprId !== null && typeof vprId !== 'string') {
    throw new Error('vpr_id must be present as string or null');
  }
  if (nonNullRequest.vpr_id !== hub.artifacts.vpr.artifact_id) {
    throw new Error('non-null vpr_id must equal VPR hub artifact_id');
  }
  validateBothTruths('CVTailoringRequest', request);
}

export function assertStatusContract(statuses: string[]): void {
  const allowed = new Set<string>(artifactStatusValues);
  for (const status of statuses) {
    if (!allowed.has(status)) {
      throw new Error(`status enum value is not FE-tolerated: ${status}`);
    }
    validateBothTruths('VPRStatusResponse', { status });
  }
}

export function assertPatchEcho(response: InterviewPrepPatchResponse): void {
  if (!response.answer || response.answer_version === undefined || !response.answer_updated_at) {
    throw new Error('PATCH response must echo result.*, version, and updated_at');
  }
  validateBothTruths('InterviewPrepPatchResponse', response);
}

export function assertRequestIdPrimacy(response: AsyncTaskResponse): string {
  const pollKey = response.request_id ?? response.job_id;
  if (!pollKey) {
    throw new Error('AsyncTaskResponse must resolve poll key from request_id ?? job_id');
  }
  return pollKey;
}

export function assertNestedResultsPreserved(fixtures: {
  vprFullData: unknown;
  cvTailored: unknown;
  interviewPrep: unknown;
  coverLetter: unknown;
}): void {
  const vprFull = fixtures.vprFullData as { roleAlignment?: { coreResponsibilities?: unknown[] } };
  if (!vprFull.roleAlignment?.coreResponsibilities?.length) {
    throw new Error('VPRFullData nested result tree was flattened or dropped');
  }
  validateBothTruths('CVTailoredStatusResponse', fixtures.cvTailored);
  validateBothTruths('InterviewPrepStatusResponse', fixtures.interviewPrep);
  validateBothTruths('CoverLetterStatusResponse', fixtures.coverLetter);
}

export function assertPresignedDownloadContract(vprStatus: VPRStatusResponse, exportResponse: ExportResponse): void {
  if (vprStatus.status === 'completed' && !vprStatus.result?.download_url) {
    throw new Error('VPR success must include result.download_url');
  }
  if (!exportResponse.download_url || !exportResponse.expires_at) {
    throw new Error('Export success must include presigned download_url and expires_at');
  }
  validateBothTruths('VPRStatusResponse', vprStatus);
  validateBothTruths('ExportResponse', exportResponse);
  validateBothTruths('VPRStatusResponse', { status: 'expired' satisfies ArtifactStatus });
}

export function assertRecentNewsPolymorphism(companyResearch: unknown): void {
  validateBothTruths('CompanyResearchResult', companyResearch);
}

export function assertFlatErrorEnvelope(errorEnvelope: unknown): void {
  const result = flatErrorEnvelopeSchema.safeParse(errorEnvelope);
  if (!result.success) {
    throw new Error(`flat error envelope required: ${result.error.issues.map((issue) => issue.path.join('.') || issue.message).join(', ')}`);
  }
  validateBothTruths('ErrorResponse', errorEnvelope);
}
