from __future__ import annotations

from careervp.models.vpr import VPR, Achievement, EvidenceItem, TargetRole, ValueProposition


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
    vpr = VPR(
        application_id='app-1',
        user_id='user-1',
        executive_summary='A strong match.',
        evidence_matrix=[
            EvidenceItem(
                requirement='Python',
                evidence='8 years with Python',
                alignment_score='STRONG',
                impact_potential='Immediate productivity',
            )
        ],
        differentiators=['Cloud migration expertise'],
        gap_strategies=[],
    )
    assert vpr.application_id == 'app-1'
    assert len(vpr.evidence_matrix) == 1
