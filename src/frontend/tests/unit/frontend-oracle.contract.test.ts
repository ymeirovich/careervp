import {
  assertApplicationIdsMatch,
  assertArtifactRoundTrip,
  assertFlatErrorEnvelope,
  assertNestedResultsPreserved,
  assertPatchEcho,
  assertPresignedDownloadContract,
  assertRecentNewsPolymorphism,
  assertRequestIdPrimacy,
  assertStatusContract,
  assertVprIdContract,
  backendSchemaNames,
  validateBothTruths,
} from '../../lib/contractOracle';
import {
  applicationHubFixture,
  asyncTaskFixtures,
  companyResearchObjectNewsFixture,
  companyResearchStringNewsFixture,
  contractFixtureCorpus,
  coverLetterStatusFixture,
  cvTailoredStatusFixture,
  cvTailoringRequestNullFixture,
  cvTailoringRequestOmittedFixture,
  cvTailoringRequestWithVprFixture,
  exportResponseFixture,
  flatErrorFixture,
  interviewPrepPatchFixture,
  interviewPrepStatusFixture,
  nestedErrorFixture,
  statusEndpointFixtures,
  vprFullDataFixture,
  vprStatusMissingDownloadFixture,
  vprStatusSuccessFixture,
} from '../contract/oracleFixtures';

describe('F-01 frontend executable oracle', () => {
  it('oracle_mirror_matches_types exposes every contract-bearing schema', () => {
    expect(backendSchemaNames).toEqual([
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
    ]);
  });

  it('oracle_be_schema_regenerates keeps committed schemas loadable', () => {
    for (const schemaName of backendSchemaNames) {
      expect(() => validateBothTruths(schemaName, contractFixtureCorpus[schemaName])).not.toThrow();
    }
  });

  it('oracle_fixture_passes_both_truths names drift for shared fixtures', () => {
    for (const [schemaName, fixture] of Object.entries(contractFixtureCorpus)) {
      expect(() => validateBothTruths(schemaName, fixture)).not.toThrow();
    }
  });

  it('oracle_catches_F02_download_url_missing', () => {
    expect(() => assertPresignedDownloadContract(vprStatusMissingDownloadFixture, exportResponseFixture)).toThrow(
      /download_url/,
    );
  });

  it('oracle_catches_F03_status_enum_gap', () => {
    expect(() => assertStatusContract(['pending', 'processing', 'completed', 'failed', 'cancelled', 'expired', 'not_generated', 'edited'])).not.toThrow();
  });

  it('oracle_catches_F04_vpr_id_null', () => {
    expect(() => assertVprIdContract(applicationHubFixture, cvTailoringRequestNullFixture, cvTailoringRequestWithVprFixture)).not.toThrow();
    expect(() => assertVprIdContract(applicationHubFixture, cvTailoringRequestOmittedFixture, cvTailoringRequestWithVprFixture)).toThrow(/absent/);
  });

  it('oracle_catches_F05_nested_error', () => {
    expect(() => assertFlatErrorEnvelope(flatErrorFixture)).not.toThrow();
    expect(() => assertFlatErrorEnvelope(nestedErrorFixture)).toThrow(/flat error envelope/);
  });
});

describe('F-06 all §3 frontend contract assertions', () => {
  it('oracle_s3_item_1_application_id_equals_job_id', () => {
    expect(() => assertApplicationIdsMatch(applicationHubFixture)).not.toThrow();
  });

  it('oracle_s3_item_2_artifact_id_round_trips_to_status_endpoint', () => {
    expect(() => assertArtifactRoundTrip(applicationHubFixture, statusEndpointFixtures)).not.toThrow();
  });

  it('oracle_s3_item_3_vpr_id_null_present_not_absent', () => {
    expect(() => assertVprIdContract(applicationHubFixture, cvTailoringRequestNullFixture, cvTailoringRequestWithVprFixture)).not.toThrow();
    expect(() => assertVprIdContract(applicationHubFixture, cvTailoringRequestOmittedFixture, cvTailoringRequestWithVprFixture)).toThrow(/absent/);
  });

  it('oracle_s3_item_4_status_enum_is_additive_only', () => {
    expect(() => assertStatusContract(['pending', 'processing', 'completed', 'failed', 'cancelled', 'expired', 'not_generated', 'edited'])).not.toThrow();
    expect(() => assertStatusContract(['pending', 'archived'])).toThrow(/archived/);
  });

  it('oracle_s3_item_5_patch_echoes_result_version_updated_at', () => {
    expect(() => assertPatchEcho(interviewPrepPatchFixture)).not.toThrow();
  });

  it('oracle_s3_item_6_request_id_primacy', () => {
    expect(assertRequestIdPrimacy(asyncTaskFixtures.requestOnly)).toBe('req-only');
    expect(assertRequestIdPrimacy(asyncTaskFixtures.jobOnly)).toBe('job-only');
    expect(assertRequestIdPrimacy(asyncTaskFixtures.both)).toBe('req-wins');
  });

  it('oracle_s3_item_7_nested_result_trees_preserved', () => {
    expect(() =>
      assertNestedResultsPreserved({
        vprFullData: vprFullDataFixture,
        cvTailored: cvTailoredStatusFixture,
        interviewPrep: interviewPrepStatusFixture,
        coverLetter: coverLetterStatusFixture,
      }),
    ).not.toThrow();
  });

  it('oracle_s3_item_8_presigned_url_and_expired_status', () => {
    expect(() => assertPresignedDownloadContract(vprStatusSuccessFixture, exportResponseFixture)).not.toThrow();
  });

  it('oracle_s3_item_9_recent_news_polymorphism', () => {
    expect(() => assertRecentNewsPolymorphism(companyResearchStringNewsFixture)).not.toThrow();
    expect(() => assertRecentNewsPolymorphism(companyResearchObjectNewsFixture)).not.toThrow();
  });

  it('oracle_s3_item_10_flat_error_envelope', () => {
    expect(() => assertFlatErrorEnvelope(flatErrorFixture)).not.toThrow();
  });
});
