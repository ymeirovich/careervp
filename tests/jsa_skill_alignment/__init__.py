"""
JSA Skill Alignment Test Suite

Test suite for JSA (Job Search Assistant) Skill Alignment implementation.

Tests are organized by component:
- test_vpr_alignment.py: VPR Prompt 6-stage methodology
- test_cv_tailoring_alignment.py: CV Tailoring 3-step verification
- test_cover_letter_alignment.py: Cover Letter scaffolded structure
- test_gap_analysis_alignment.py: Gap Analysis contextual tagging
- test_interview_prep_alignment.py: Interview Prep Generator
- test_quality_validator_alignment.py: Quality Validator Agent
- test_knowledge_base_alignment.py: Knowledge Base for user memory

All tests map to requirements in:
- docs/architecture/jsa-skill-alignment/JSA-Skill-Alignment-Plan.md
- docs/specs/05-jsa-skill-alignment.md

Run tests:
    uv run pytest tests/jsa_skill_alignment/ -v
"""

from __future__ import annotations
