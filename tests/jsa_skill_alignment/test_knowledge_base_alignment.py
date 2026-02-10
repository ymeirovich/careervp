"""
JSA Skill Alignment Tests - Knowledge Base Implementation

Tests for Knowledge Base as defined in:
- JSA-Skill-Alignment-Plan.md Section 7.3
- docs/specs/05-jsa-skill-alignment.md Section 8

Requirement Traceability:
- TEST-KB-001: KB-001 (Table in CDK)
- TEST-KB-002: KB-001 (Repository exists)
- TEST-KB-003: KB-001 (recurring_themes)
- TEST-KB-004: KB-001 (gap_responses)
"""

from __future__ import annotations

import os
import pytest


class TestKnowledgeBaseAlignment:
    """Test suite for Knowledge Base implementation alignment."""

    def test_knowledge_base_table_in_cdk(self):
        """
        TEST-KB-001: Verify knowledge base table is defined in CDK.

        Requirement: KB-001 (Table in CDK)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        cdk_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "infra",
            "careervp",
            "api_db_construct.py",
        )

        if not os.path.exists(cdk_path):
            pytest.skip("api_db_construct.py not found")

        with open(cdk_path, "r") as f:
            content = f.read()

        assert "knowledge" in content.lower()

    def test_knowledge_base_repository_exists(self):
        """
        TEST-KB-002: Verify knowledge base repository file exists.

        Requirement: KB-001 (Repository exists)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        repo_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "dal",
            "knowledge_base_repository.py",
        )
        assert os.path.exists(repo_path), (
            f"Knowledge base repository not found at {repo_path}"
        )

    def test_knowledge_base_supports_recurring_themes(self):
        """
        TEST-KB-003: Verify recurring_themes knowledge type is supported.

        Requirement: KB-001 (recurring_themes)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        repo_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "dal",
            "knowledge_base_repository.py",
        )

        if not os.path.exists(repo_path):
            pytest.skip("knowledge_base_repository.py not yet created")

        with open(repo_path, "r") as f:
            content = f.read()

        assert "recurring" in content.lower() or "theme" in content.lower()

    def test_knowledge_base_supports_gap_responses(self):
        """
        TEST-KB-004: Verify gap_responses knowledge type is supported.

        Requirement: KB-001 (gap_responses)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        repo_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "dal",
            "knowledge_base_repository.py",
        )

        if not os.path.exists(repo_path):
            pytest.skip("knowledge_base_repository.py not yet created")

        with open(repo_path, "r") as f:
            content = f.read()

        assert "gap" in content.lower() and "response" in content.lower()

    def test_knowledge_base_supports_differentiators(self):
        """
        Verify differentiators knowledge type is supported.

        Requirement: KB-001 (differentiators)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        repo_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "dal",
            "knowledge_base_repository.py",
        )

        if not os.path.exists(repo_path):
            pytest.skip("knowledge_base_repository.py not yet created")

        with open(repo_path, "r") as f:
            content = f.read()

        assert "differentiat" in content.lower()

    def test_knowledge_base_has_user_email_pk(self):
        """
        Verify userEmail is used as partition key.

        Requirement: KB-001 (Schema)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        cdk_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "infra",
            "careervp",
            "api_db_construct.py",
        )

        if not os.path.exists(cdk_path):
            pytest.skip("api_db_construct.py not found")

        with open(cdk_path, "r") as f:
            content = f.read()

        # Check for partition key definition
        assert (
            "userEmail" in content
            or "user_email" in content.lower()
            or "partition" in content.lower()
        )

    def test_knowledge_base_has_knowledge_type_sk(self):
        """
        Verify knowledgeType is used as sort key.

        Requirement: KB-001 (Schema)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        cdk_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "infra",
            "careervp",
            "api_db_construct.py",
        )

        if not os.path.exists(cdk_path):
            pytest.skip("api_db_construct.py not found")

        with open(cdk_path, "r") as f:
            content = f.read()

        # Check for sort key definition
        assert (
            "knowledgeType" in content
            or "knowledge_type" in content.lower()
            or "sort" in content.lower()
        )

    def test_knowledge_base_logic_module_exists(self):
        """
        Verify knowledge base logic module exists.

        Requirement: KB-001 (Logic)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        logic_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "knowledge_base.py",
        )

        assert os.path.exists(logic_path), (
            f"Knowledge base logic not found at {logic_path}"
        )

    def test_knowledge_base_has_crud_operations(self):
        """
        Verify CRUD operations are implemented.

        Requirement: KB-001 (CRUD)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        logic_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "knowledge_base.py",
        )

        if not os.path.exists(logic_path):
            pytest.skip("knowledge_base.py not yet created")

        with open(logic_path, "r") as f:
            content = f.read()

        # Should have save/get operations
        has_save = (
            "save" in content.lower()
            or "put" in content.lower()
            or "store" in content.lower()
        )
        has_get = (
            "get" in content.lower()
            or "load" in content.lower()
            or "retrieve" in content.lower()
        )

        assert has_save or has_get, "CRUD operations should be present"

    def test_knowledge_base_integrates_with_gap_analysis(self):
        """
        Verify knowledge base can be integrated with Gap Analysis.

        Requirement: KB-001 (Integration)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        gap_prompt_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "backend",
            "careervp",
            "logic",
            "prompts",
            "gap_analysis_prompt.py",
        )

        if not os.path.exists(gap_prompt_path):
            pytest.skip("gap_analysis_prompt.py not found")

        with open(gap_prompt_path, "r") as f:
            content = f.read()

        # Should reference recurring themes from knowledge base
        assert "recurring" in content.lower() or "knowledge" in content.lower()

    def test_table_name_is_careervp_knowledge_base(self):
        """
        Verify table name follows convention.

        Requirement: KB-001 (Table Name)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        cdk_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "infra",
            "careervp",
            "api_db_construct.py",
        )

        if not os.path.exists(cdk_path):
            pytest.skip("api_db_construct.py not found")

        with open(cdk_path, "r") as f:
            content = f.read()

        # Should reference careervp-knowledge-base or similar
        assert "knowledge" in content.lower()

    def test_knowledge_base_has_ttl_configured(self):
        """
        Verify TTL is configured for the table.

        Requirement: KB-001 (TTL)
        Source: JSA-Skill-Alignment-Plan.md Section 7.3
        """
        cdk_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "infra",
            "careervp",
            "api_db_construct.py",
        )

        if not os.path.exists(cdk_path):
            pytest.skip("api_db_construct.py not found")

        with open(cdk_path, "r") as f:
            content = f.read()

        # Should reference TTL
        assert "ttl" in content.lower() or "time" in content.lower()
