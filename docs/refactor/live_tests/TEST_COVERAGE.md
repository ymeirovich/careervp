# Live Test Coverage Matrix

## Overview

This document maps each live test to its corresponding feature in the execution runbooks and API endpoint in the OpenAPI specification.

## Test to Feature & Endpoint Mapping

| Test File | Test Class | Feature | Swagger Endpoint | Method | Runbook Reference |
|-----------|------------|---------|------------------|--------|-------------------|
| `test_01_auth_health.py` | `TestHealthEndpoint` | Health Check | `/health` | GET | Phase 10.10 |
| `test_01_auth_health.py` | `TestAuthEndpoints` | User Registration | `/auth/register` | POST | Phase 10.1 |
| `test_01_auth_health.py` | `TestAuthEndpoints` | User Login | `/auth/login` | POST | Phase 10.1 |
| `test_01_auth_health.py` | `TestAuthEndpoints` | Token Refresh | `/auth/refresh` | POST | Phase 10.1 |
| `test_02_users.py` | `TestUserEndpoints` | Get Current User | `/users/me` | GET | Phase 10.2 |
| `test_02_users.py` | `TestUserEndpoints` | Update Current User | `/users/me` | PUT | Phase 10.2 |
| `test_02_users.py` | `TestUserEndpoints` | Upload CV | `/users/me/cv` | POST | Phase 10.2, CV Upload Feature |
| `test_02_users.py` | `TestUserEndpoints` | List User CVs | `/users/me/cvs` | GET | Phase 10.2 |
| `test_03_jobs.py` | `TestJobEndpoints` | Create Job | `/jobs` | POST | Phase 10.3 |
| `test_03_jobs.py` | `TestJobEndpoints` | List Jobs | `/jobs` | GET | Phase 10.3 |
| `test_03_jobs.py` | `TestJobEndpoints` | Get Job | `/jobs/{jobId}` | GET | Phase 10.3 |
| `test_04_vpr.py` | `TestVPREndpoints` | Generate VPR | `/vpr/generate` | POST | Phase 10.4, VPR Feature |
| `test_04_vpr.py` | `TestVPREndpoints` | Get VPR Status | `/vpr/{vprId}` | GET | Phase 10.4 |
| `test_04_vpr.py` | `TestVPREndpoints` | List User VPRs | `/users/me/vprs` | GET | Phase 10.4 |
| `test_04_vpr.py` | `TestVPREndpoints` | VPR Async Polling | `/vpr/{vprId}` | GET | Phase 10.4 |
| `test_05_gap_analysis.py` | `TestGapAnalysisEndpoints` | Generate Gap Questions | `/gap-analysis/questions` | POST | Phase 10.5, Gap Analysis Feature |
| `test_05_gap_analysis.py` | `TestGapAnalysisEndpoints` | Submit Gap Responses | `/gap-analysis/responses` | POST | Phase 10.5, Gap Analysis Feature |
| `test_05_gap_analysis.py` | `TestGapAnalysisEndpoints` | Get Gap Questions | `/gap-analysis/{jobId}/questions` | GET | Phase 10.5 |
| `test_06_cv_tailoring.py` | `TestCVTailoringEndpoints` | Generate Tailored CV | `/cv-tailoring/generate` | POST | Phase 10.6, CV Tailoring Feature |
| `test_06_cv_tailoring.py` | `TestCVTailoringEndpoints` | Get Tailored CV Status | `/cv-tailoring/{cvTailoringId}` | GET | Phase 10.6 |
| `test_06_cv_tailoring.py` | `TestCVTailoringEndpoints` | List Tailored CVs | `/users/me/tailored-cvs` | GET | Phase 10.6 |
| `test_06_cv_tailoring.py` | `TestCVTailoringEndpoints` | CV Tailoring Async | `/cv-tailoring/{cvTailoringId}` | GET | Phase 10.6 |
| `test_07_cover_letter.py` | `TestCoverLetterEndpoints` | Generate Cover Letter | `/cover-letter/generate` | POST | Phase 10.7, Cover Letter Feature |
| `test_07_cover_letter.py` | `TestCoverLetterEndpoints` | Get Cover Letter Status | `/cover-letter/{coverLetterId}` | GET | Phase 10.7 |
| `test_07_cover_letter.py` | `TestCoverLetterEndpoints` | List Cover Letters | `/users/me/cover-letters` | GET | Phase 10.7 |
| `test_07_cover_letter.py` | `TestCoverLetterEndpoints` | Cover Letter Async | `/cover-letter/{coverLetterId}` | GET | Phase 10.7 |
| `test_08_interview_prep.py` | `TestInterviewPrepEndpoints` | Generate Interview Prep | `/interview-prep/generate` | POST | Phase 10.8, Interview Prep Feature |
| `test_08_interview_prep.py` | `TestInterviewPrepEndpoints` | Get Interview Prep Status | `/interview-prep/{interviewPrepId}` | GET | Phase 10.8 |
| `test_08_interview_prep.py` | `TestInterviewPrepEndpoints` | Interview Prep Async | `/interview-prep/{interviewPrepId}` | GET | Phase 10.8 |
| `test_09_company_research.py` | `TestCompanyResearchEndpoints` | Fetch Company Research | `/company-research/fetch` | POST | Phase 10.9, Company Research Feature |
| `test_09_company_research.py` | `TestCompanyResearchEndpoints` | Get Company Research | `/company-research/{jobId}` | GET | Phase 10.9 |
| `test_09_company_research.py` | `TestCompanyResearchEndpoints` | Company Research Async | `/company-research/{jobId}` | GET | Phase 10.9 |

## Feature Coverage Summary

| Feature | Description | Test Files | Endpoint Count |
|---------|-------------|------------|----------------|
| **CV Upload** | Upload CV to S3, record in DynamoDB | test_02_users.py | 2 |
| **Gap Analysis** | Generate questions + submit responses (CV + Company Research + Job Description → Gap Questions) | test_05_gap_analysis.py | 3 |
| **VPR Generation** | Generate Value Proposition Report from Gap Analysis responses | test_04_vpr.py | 3 |
| **ATS-Optimized CV** | Generate tailored CV using VPR + Gap Analysis | test_06_cv_tailoring.py | 3 |
| **Cover Letter** | Generate 3-paragraph cover letter using VPR + CV + Company Research | test_07_cover_letter.py | 3 |
| **Interview Prep** | Generate STAR-formatted questions using VPR + CV + Company Research | test_08_interview_prep.py | 2 |
| **Company Research** | Fetch and research company from URL | test_09_company_research.py | 2 |

## Total Coverage

| Metric | Count |
|--------|-------|
| **Total Test Files** | 9 |
| **Total Test Classes** | 9 |
| **Total Test Methods** | 32 |
| **API Endpoints Covered** | 27/27 (100%) |
| **Features Covered** | 7/7 (100%) |

## Workflow Integration Tests

The live tests also include workflow integration tests that verify the complete user journey:

1. **CV → Gap Analysis → VPR → CV Tailoring**
2. **CV → Gap Analysis → VPR → Cover Letter**
3. **CV → Gap Analysis → VPR → Interview Prep**
4. **Job → Company Research → All Features**

These are implemented through test data sharing between test files via the `test_data` dictionary.
