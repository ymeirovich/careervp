"""Registry of P-05 cross-tenant owner-check cases (read by the ratchet + the cross-tenant probe).

Not a test file. One case per handler that serves a foreign-resource-id route, exercising the READ
path where a cross-tenant leak is observable. ``COVERED_HANDLERS`` is what the ratchet in
``tests/unit/test_p04_p05_auth_idor.py`` checks the live route_map against: if a new resource-by-id
route appears whose handler is not covered here, the ratchet fails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from tests.integration import p05_seeding as seeding


@dataclass(frozen=True)
class OwnerCheckCase:
    route_id: str
    handler_attr: str
    handler_import: str  # "module.path:callable"
    path: str
    method: str
    seeder: Callable[[str], str]
    # given the seeded resource id, build the path parameters the handler extracts
    path_params: Callable[[str], dict[str, str]] = field(default=lambda rid: {})


CASES: list[OwnerCheckCase] = [
    OwnerCheckCase(
        route_id='jobs.get',
        handler_attr='job_api_func',
        handler_import='careervp.handlers.job_handler:lambda_handler',
        path='/jobs/{jobId}',
        method='GET',
        seeder=seeding.seed_job,
        path_params=lambda rid: {'jobId': rid},
    ),
    OwnerCheckCase(
        route_id='gap.questions.get',
        handler_attr='gap_api_func',
        handler_import='careervp.handlers.gap_handler:lambda_handler',
        path='/jobs/{jobId}/gap-questions',
        method='GET',
        seeder=seeding.seed_gap_questions,
        path_params=lambda rid: {'jobId': rid},
    ),
    OwnerCheckCase(
        route_id='applications.get',
        handler_attr='application_api_func',
        handler_import='careervp.handlers.application_handler:lambda_handler',
        path='/applications/{application_id}',
        method='GET',
        seeder=seeding.seed_application,
        path_params=lambda rid: {'application_id': rid},
    ),
    OwnerCheckCase(
        route_id='vpr.status.get',
        handler_attr='vpr_status_func',
        handler_import='careervp.handlers.vpr_status_handler:lambda_handler',
        path='/vpr/{vprId}/status',
        method='GET',
        seeder=seeding.seed_vpr_job,
        path_params=lambda rid: {'vprId': rid},
    ),
    OwnerCheckCase(
        route_id='cv-tailoring.status.get',
        handler_attr='cv_tailoring_func',
        handler_import='careervp.handlers.cv_tailoring_handler:handler',
        path='/cv-tailoring/{cvTailoringId}/status',
        method='GET',
        seeder=seeding.seed_cv_tailoring,
        path_params=lambda rid: {'cvTailoringId': rid},
    ),
    OwnerCheckCase(
        route_id='cover-letter.status.get',
        handler_attr='cover_letter_status_func',
        handler_import='careervp.handlers.cover_letter_handler:lambda_handler',
        path='/cover-letter/{coverLetterId}/status',
        method='GET',
        seeder=seeding.seed_cover_letter,
        path_params=lambda rid: {'coverLetterId': rid},
    ),
    OwnerCheckCase(
        route_id='interview-prep.status.get',
        handler_attr='interview_prep_status_func',
        handler_import='careervp.handlers.interview_prep_handler:lambda_handler',
        path='/interview-prep/{interviewPrepId}/status',
        method='GET',
        seeder=seeding.seed_interview_prep,
        path_params=lambda rid: {'interviewPrepId': rid},
    ),
    OwnerCheckCase(
        route_id='company-research.get',
        handler_attr='company_research_func',
        handler_import='careervp.handlers.company_research_handler:lambda_handler',
        path='/company-research/{jobId}',
        method='GET',
        seeder=seeding.seed_company_research,
        path_params=lambda rid: {'jobId': rid},
    ),
    OwnerCheckCase(
        route_id='jobs.export.get',
        handler_attr='export_lambda',
        handler_import='careervp.handlers.export_handler:lambda_handler',
        path='/jobs/{jobId}/artifacts/{moduleType}/export',
        method='GET',
        seeder=seeding.seed_export_artifact,
        path_params=lambda rid: {'jobId': rid, 'moduleType': 'cv_tailored'},
    ),
]

COVERED_HANDLERS: frozenset[str] = frozenset(case.handler_attr for case in CASES)
