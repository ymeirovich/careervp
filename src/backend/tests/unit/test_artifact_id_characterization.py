"""Characterize artifact-id behavior before D-H4/P-01 routing changes.

Public artifact identifiers remain opaque request/job ids. The storage layer
maps those values to the established type-specific key grammar; D-H4 may move
resolution behind ``CoreRepository`` but must not change these observable
identity mappings.
"""

from __future__ import annotations

from careervp.dal import table_registry
from careervp.dal.dynamo_dal_handler import DynamoDalHandler


def test_vpr_artifact_id_uses_versioned_storage_identity() -> None:
    assert DynamoDalHandler._build_vpr_sort_key(1) == 'ARTIFACT#VPR#v1'


def test_cv_tailoring_artifact_id_maps_from_opaque_request_id() -> None:
    assert table_registry.tailored_cv_artifact_id('cv-tailoring-001') == 'ARTIFACT#CV_TAILORED#cv-tailoring-001'


def test_cover_letter_artifact_id_maps_from_opaque_request_id() -> None:
    assert table_registry.cover_letter_artifact_id('cl-001') == 'ARTIFACT#COVER_LETTER#cl-001'


def test_interview_prep_artifact_id_maps_from_opaque_request_id() -> None:
    assert table_registry.interview_prep_artifact_id('ip-001') == 'ARTIFACT#INTERVIEW_PREP#ip-001'
