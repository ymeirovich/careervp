from __future__ import annotations

from careervp.models.vpr import VPR, Achievement, TargetRole, ValueProposition


def test_new_vpr_models_exist() -> None:
    assert ValueProposition is not None
    assert Achievement is not None
    assert TargetRole is not None


def test_achievement_model_accepts_expected_fields() -> None:
    achievement = Achievement(description='Reduced latency by 40%', impact='Improved customer experience', metric='40%')
    assert achievement.description == 'Reduced latency by 40%'
    assert achievement.impact == 'Improved customer experience'
    assert achievement.metric == '40%'


def test_target_role_model_accepts_expected_fields() -> None:
    role = TargetRole(title='Senior Engineer', company='TechCo', industry='SaaS')
    assert role.title == 'Senior Engineer'
    assert role.company == 'TechCo'
    assert role.industry == 'SaaS'


def test_value_proposition_references_achievement_and_target_role() -> None:
    value_prop = ValueProposition(
        headline='Platform modernization leader',
        summary='Built and scaled cloud services.',
        target_role=TargetRole(title='Principal Engineer'),
        achievements=[Achievement(description='Cut infra cost by 25%')],
    )
    assert value_prop.target_role is not None
    assert len(value_prop.achievements) == 1
    assert value_prop.achievements[0].description == 'Cut infra cost by 25%'


def test_existing_vpr_models_still_work() -> None:
    """VPR model accepts minimal required fields; all 10 sections are optional for legacy compat."""
    vpr = VPR(
        application_id='app-1',
        user_id='user-1',
    )
    assert vpr.application_id == 'app-1'
    assert vpr.user_id == 'user-1'
    # All 10 content sections are optional (None by default) for legacy DynamoDB items
    assert vpr.executive_summary is None
    assert vpr.evidence_gaps is None
