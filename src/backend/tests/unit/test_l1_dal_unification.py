"""
L1.2 — DAL Unification Unit Tests

Validates: CVTable fully replaced by DynamoDalHandler across all handlers/DAL files
Spec: docs/best_practices/yaml/dynamodb_modeling_spec.yaml
Payload: docs/refactor/payloads/beta_l1_persistence_test.json#L1_2_dal_unification
Invariant: I2
Results: docs/beta/execution_results/L1_2_results.md
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('DYNAMODB_TABLE_NAME', 'careervp-users-table-test')
os.environ.setdefault('ENVIRONMENT', 'test')

BACKEND_DIR = str(Path(__file__).resolve().parents[2])


@pytest.fixture
def mock_dal():
    with patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler') as mock_cls:
        mock_instance = MagicMock()
        mock_instance.get_item.return_value = {'pk': 'USER#u1', 'sk': 'CV#cv1', 'content': 'test'}
        mock_instance.put_item.return_value = {}
        mock_instance.query.return_value = {'Items': [], 'Count': 0}
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.mark.unit
class TestNoCVTableImports:
    """CVTable must not be imported anywhere in handlers or DAL (except cv_dal.py itself)."""

    def test_no_cvtable_imports_in_handlers(self):
        """grep for CVTable in handlers/ .py files returns 0 matches."""
        result = subprocess.run(['grep', '-r', '--include=*.py', 'CVTable', 'careervp/handlers/'], capture_output=True, text=True, cwd=BACKEND_DIR)
        assert result.returncode != 0, f'CVTable still imported in handlers:\n{result.stdout.strip()}'

    def test_no_cvtable_imports_in_logic(self):
        """grep for CVTable in logic/ .py files returns 0 matches."""
        result = subprocess.run(['grep', '-r', '--include=*.py', 'CVTable', 'careervp/logic/'], capture_output=True, text=True, cwd=BACKEND_DIR)
        assert result.returncode != 0, f'CVTable still used in logic:\n{result.stdout.strip()}'

    def test_no_cv_table_module_imports(self):
        """grep for 'from careervp.dal.cv_dal import CVTable' returns 0 matches outside cv_dal.py."""
        result = subprocess.run(
            ['grep', '-r', '--include=*.py', 'from careervp.dal.cv_dal import CVTable', 'careervp/'], capture_output=True, text=True, cwd=BACKEND_DIR
        )
        lines = [line for line in result.stdout.splitlines() if 'cv_dal.py' not in line]
        assert lines == [], 'CVTable imported outside cv_dal.py:\n' + '\n'.join(lines)

    def test_cover_letter_handler_no_cvtable(self):
        """cover_letter_handler.py has no CVTable references."""
        result = subprocess.run(
            ['grep', '--include=*.py', 'CVTable', 'careervp/handlers/cover_letter_handler.py'], capture_output=True, text=True, cwd=BACKEND_DIR
        )
        assert result.returncode != 0, f'CVTable still in cover_letter_handler:\n{result.stdout.strip()}'

    def test_interview_prep_handler_no_cvtable(self):
        """interview_prep_handler.py has no CVTable references."""
        result = subprocess.run(
            ['grep', '--include=*.py', 'CVTable', 'careervp/handlers/interview_prep_handler.py'], capture_output=True, text=True, cwd=BACKEND_DIR
        )
        assert result.returncode != 0, f'CVTable still in interview_prep_handler:\n{result.stdout.strip()}'

    def test_cv_tailoring_handler_no_cvtable(self):
        """cv_tailoring_handler.py has no CVTable references."""
        result = subprocess.run(
            ['grep', '--include=*.py', 'CVTable', 'careervp/handlers/cv_tailoring_handler.py'], capture_output=True, text=True, cwd=BACKEND_DIR
        )
        assert result.returncode != 0, f'CVTable still in cv_tailoring_handler:\n{result.stdout.strip()}'


@pytest.mark.unit
class TestCVDalUsesDynamoDalHandler:
    """DynamoDalHandler is used for CV persistence (not CVTable)."""

    def test_dynamo_dal_handler_has_save_cv(self):
        """DynamoDalHandler has save_cv() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        assert hasattr(DynamoDalHandler, 'save_cv'), 'DynamoDalHandler missing save_cv()'

    def test_dynamo_dal_handler_has_get_cv(self):
        """DynamoDalHandler has get_cv() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        assert hasattr(DynamoDalHandler, 'get_cv'), 'DynamoDalHandler missing get_cv()'

    def test_dynamo_dal_handler_has_list_cover_letters(self):
        """DynamoDalHandler has list_cover_letters() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        assert hasattr(DynamoDalHandler, 'list_cover_letters'), 'DynamoDalHandler missing list_cover_letters()'

    def test_dynamo_dal_handler_has_list_tailored_cvs(self):
        """DynamoDalHandler has list_tailored_cvs() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        assert hasattr(DynamoDalHandler, 'list_tailored_cvs'), 'DynamoDalHandler missing list_tailored_cvs()'

    def test_dynamo_dal_handler_has_save_cover_letter(self):
        """DynamoDalHandler has save_cover_letter() method."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        assert hasattr(DynamoDalHandler, 'save_cover_letter'), 'DynamoDalHandler missing save_cover_letter()'

    def test_cv_save_calls_put_item(self):
        """save_cv() calls dal.put_item with correct pk/sk schema."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        from careervp.models.cv import UserCV

        with patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler') as mock_table:
            mock_tbl = MagicMock()
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler('test-table')
            user_cv = UserCV(
                user_id='USER#user-test-123',
                cv_id='cv-abc456',
                full_name='Test User',
            )
            dal.save_cv(user_cv)
            mock_tbl.put_item.assert_called_once()
            item = mock_tbl.put_item.call_args[1]['Item']
            assert item['pk'] == 'USER#user-test-123', f'Wrong pk: {item.get("pk")}'

    def test_cv_list_calls_query_not_scan(self):
        """list_tailored_cvs() calls table.query(), never table.scan()."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        with patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler') as mock_table:
            mock_tbl = MagicMock()
            mock_tbl.query.return_value = {'Items': [], 'Count': 0}
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler('test-table')
            dal.list_tailored_cvs('user-test-123')
            mock_tbl.query.assert_called_once()
            mock_tbl.scan.assert_not_called()


@pytest.mark.unit
class TestDynamoDalHandlerSchema:
    """DynamoDalHandler uses correct single-table pk/sk schema."""

    def test_cover_letter_sk_prefix(self):
        """save_cover_letter() sk starts with 'ARTIFACT#COVER_LETTER#'."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        with patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler') as mock_table:
            mock_tbl = MagicMock()
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler('test-table')
            dal.save_cover_letter(
                cover_letter={'text': 'Dear Hiring Manager,'},
                user_id='user-test-123',
                cv_id='cv-abc456',
                job_id='job-xyz789',
            )
            mock_tbl.put_item.assert_called_once()
            item = mock_tbl.put_item.call_args[1]['Item']
            assert item['sk'].startswith('ARTIFACT#COVER_LETTER#'), f'Wrong sk prefix: {item.get("sk")}'

    def test_vpr_sk_prefix(self):
        """save_vpr() sk starts with 'ARTIFACT#VPR#'."""
        from datetime import datetime, timezone

        from careervp.dal.dynamo_dal_handler import DynamoDalHandler
        from careervp.models.vpr import (
            VPR,
            VPRApplicationStrategy,
            VPRConcern,
            VPRConcernsAndMitigations,
            VPRDifferentiators,
            VPREvidenceGaps,
            VPRExecutiveSummary,
            VPRExperienceMapping,
            VPRIdentifiedGap,
            VPRKeyAchievement,
            VPRKeywordGroup,
            VPRMetadata,
            VPRMitigation,
            VPRObjection,
            VPRPrimaryValue,
            VPRPriorityGap,
            VPRRelevantExperience,
            VPRRequirementBreakdown,
            VPRResponsibility,
            VPRRoleAlignment,
            VPRSecondaryValue,
            VPRSkillsAnalysis,
            VPRStrength,
            VPRUniqueStrength,
            VPRValueProposition,
        )

        with patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler') as mock_table:
            mock_tbl = MagicMock()
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler('test-table')
            vpr = VPR(
                user_id='user-test-123',
                application_id='app-001',
                metadata=VPRMetadata(
                    report_date='2024-01-15',
                    candidate_name='Test Candidate',
                    target_role='Senior Python Engineer',
                    target_company='Tech Corp',
                ),
                executive_summary=VPRExecutiveSummary(
                    overall_fit_score=80,
                    fit_rationale=(
                        'Senior Python engineer delivering 40% cost reduction with proven cloud architecture skills '
                        'that directly align with the core infrastructure requirements.'
                    ),
                    top_three_strengths=[
                        VPRStrength(strength='Python expertise', evidence='8 years Python', relevance_to_role='Core stack'),
                        VPRStrength(strength='Cost reduction track record', evidence='40% cost cut', relevance_to_role='Efficiency'),
                        VPRStrength(strength='Cloud architecture', evidence='AWS production systems', relevance_to_role='Infrastructure'),
                    ],
                    top_three_concerns=[
                        VPRConcern(concern='Limited ML background', severity='low', mitigation='Adjacent data work'),
                        VPRConcern(concern='No team leadership listed', severity='medium', mitigation='Highlight mentoring'),
                        VPRConcern(concern='Domain experience gap', severity='low', mitigation='Transfer skills'),
                    ],
                    recommended_approach='apply_with_customization',
                ),
                role_alignment=VPRRoleAlignment(
                    core_responsibilities=[
                        VPRResponsibility(
                            responsibility='Backend Python development',
                            alignment_score=90,
                            candidate_evidence=['8 years Python development'],
                            evidence_quality='direct',
                        )
                    ],
                    requirement_breakdown=VPRRequirementBreakdown(must_have=[], nice_to_have=[], assumed_prerequisites=[]),
                ),
                experience_mapping=VPRExperienceMapping(
                    relevant_experiences=[
                        VPRRelevantExperience(
                            role='Senior Python Engineer',
                            organization='Tech Corp',
                            duration='3 years',
                            key_achievements=[VPRKeyAchievement(achievement='Cost reduction', metric='40%', impact='Saved $200k')],
                            relevance_to_target_role='Direct match',
                        )
                    ],
                    experience_gaps=[],
                ),
                skills_analysis=VPRSkillsAnalysis(technical_skills=[], soft_skills=[], tool_proficiency=[]),
                evidence_gaps=VPREvidenceGaps(
                    identified_gaps=[
                        VPRIdentifiedGap(
                            requirement='ML experience',
                            current_evidence='Adjacent data work',
                            gap_severity='low',
                            suggested_evidence=['ML projects'],
                        )
                    ],
                    priority_gaps_to_address=[
                        VPRPriorityGap(gap='ML experience', priority=1, action_item='Complete ML course', deadline='nice_to_have')
                    ],
                ),
                differentiators=VPRDifferentiators(
                    unique_strengths=[
                        VPRUniqueStrength(
                            strength='Cost reduction engineering',
                            rarity='uncommon',
                            relevance='Efficiency focus',
                            proof='40% cost reduction delivered',
                        )
                    ],
                    competitive_advantages=[],
                    positioning_statement=(
                        'Proven Python engineer combining deep backend expertise with cost-reduction track record '
                        'and scalable cloud architecture skills that deliver measurable business impact.'
                    ),
                ),
                concerns_and_mitigations=VPRConcernsAndMitigations(
                    likely_objections=[
                        VPRObjection(
                            objection='Limited ML background',
                            likelihood='unlikely',
                            mitigation=VPRMitigation(
                                strategy='show_analogous_experience',
                                messaging='Data pipeline work demonstrates ML adjacency.',
                            ),
                            where_to_address=['interview'],
                        )
                    ],
                    preemptive_responses=[],
                ),
                value_proposition=VPRValueProposition(
                    primary_value=VPRPrimaryValue(
                        statement='Reduce infrastructure cost',
                        evidence='40% cost reduction at previous role',
                        outcome_for_company='Significant infrastructure savings',
                    ),
                    secondary_values=[
                        VPRSecondaryValue(value='Delivery speed', proof='Reduced deploy time by 30%'),
                        VPRSecondaryValue(value='Code quality', proof='Zero critical bugs in production'),
                    ],
                    quantified_impact=[],
                    elevator_pitch=(
                        'Senior Python engineer with proven track record of delivering 40% cost reductions '
                        'through cloud-native architecture and disciplined engineering practices.'
                    ),
                ),
                application_strategy=VPRApplicationStrategy(
                    messaging_approach='Lead with cost reduction track record and cloud expertise.',
                    ats_keywords=VPRKeywordGroup(primary=['Python', 'AWS'], secondary=['Cost optimization']),
                    cv_lead_differentiator='Backend engineer with measurable cost reduction impact.',
                    sections_to_compress=[],
                ),
                created_at=datetime.now(timezone.utc),
            )
            dal.save_vpr(vpr)
            mock_tbl.put_item.assert_called_once()
            item = mock_tbl.put_item.call_args[1]['Item']
            assert item['sk'].startswith('ARTIFACT#VPR#'), f'Wrong sk prefix: {item.get("sk")}'

    def test_gap_questions_sk_prefix(self):
        """save_gap_questions() sk starts with 'ARTIFACT#GAP_ANALYSIS#'."""
        from careervp.dal.dynamo_dal_handler import DynamoDalHandler

        with patch('careervp.dal.dynamo_dal_handler.DynamoDalHandler._get_db_handler') as mock_table:
            mock_tbl = MagicMock()
            mock_table.return_value = mock_tbl
            dal = DynamoDalHandler('test-table')
            dal.save_gap_questions(
                user_id='user-test-123',
                cv_id='cv-abc456',
                job_id='job-xyz789',
                questions=[{'question': 'Tell me about yourself'}],
            )
            mock_tbl.put_item.assert_called_once()
            item = mock_tbl.put_item.call_args[1]['Item']
            assert item['sk'].startswith('ARTIFACT#GAP_ANALYSIS#'), f'Wrong sk prefix: {item.get("sk")}'
