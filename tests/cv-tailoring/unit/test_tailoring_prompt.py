"""Tests for CV tailoring prompt construction."""

from careervp.logic.cv_tailoring_prompt import (
    build_system_prompt,
    build_user_prompt,
    format_cv_for_prompt,
    format_job_description,
    annotate_with_relevance_scores,
    include_fvs_constraints,
    include_keyword_targets,
    format_preferences,
)


def test_build_system_prompt_structure():
    """Test system prompt has correct structure."""
    # Act
    prompt = build_system_prompt()

    # Assert
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "tailor" in prompt.lower() or "cv" in prompt.lower()
    assert "instructions" in prompt.lower() or "role" in prompt.lower()


def test_build_system_prompt_includes_constraints():
    """Test system prompt includes FVS constraints."""
    # Act
    prompt = build_system_prompt()

    # Assert
    assert "immutable" in prompt.lower() or "do not change" in prompt.lower()
    assert "dates" in prompt.lower() or "employment" in prompt.lower()


def test_build_user_prompt_includes_relevance_scores(
    sample_master_cv, sample_job_description, sample_relevance_scores
):
    """Test user prompt includes relevance score annotations."""
    # Act
    prompt = build_user_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        relevance_scores=sample_relevance_scores,
    )

    # Assert
    assert "relevance" in prompt.lower()
    # Check high-scoring sections are highlighted
    for section, score in sample_relevance_scores.items():
        if score > 0.8:
            assert str(int(score * 100)) in prompt or f"{score:.2f}" in prompt


def test_build_prompt_includes_fvs_rules(
    sample_master_cv, sample_job_description, sample_fvs_baseline
):
    """Test prompt includes FVS immutable facts."""
    # Act
    prompt = build_user_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        fvs_baseline=sample_fvs_baseline,
    )

    # Assert
    assert "immutable" in prompt.lower() or "must not change" in prompt.lower()
    # Check critical facts are listed
    immutable_values = [fact.value for fact in sample_fvs_baseline.immutable_facts]
    assert any(value in prompt for value in immutable_values[:3])


def test_build_prompt_includes_target_keywords(
    sample_master_cv, sample_job_description, sample_keyword_list
):
    """Test prompt includes target keywords from job."""
    # Act
    prompt = build_user_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        target_keywords=sample_keyword_list,
    )

    # Assert
    assert "keywords" in prompt.lower() or "target" in prompt.lower()
    # Check at least 3 keywords are mentioned
    keyword_count = sum(1 for keyword in sample_keyword_list if keyword in prompt)
    assert keyword_count >= 3


def test_build_prompt_with_tone_preferences(
    sample_master_cv, sample_job_description, sample_tailoring_preferences
):
    """Test prompt includes tone preference directives."""
    # Act
    prompt = build_user_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        preferences=sample_tailoring_preferences,
    )

    # Assert
    assert sample_tailoring_preferences.tone in prompt.lower()


def test_build_prompt_with_length_preferences(
    sample_master_cv, sample_job_description, sample_tailoring_preferences
):
    """Test prompt includes length constraints."""
    # Act
    prompt = build_user_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        preferences=sample_tailoring_preferences,
    )

    # Assert
    assert (
        sample_tailoring_preferences.target_length.replace("_", " ") in prompt.lower()
    )


def test_format_cv_for_prompt(sample_master_cv):
    """Test CV formatting for prompt."""
    # Act
    formatted = format_cv_for_prompt(sample_master_cv)

    # Assert
    assert isinstance(formatted, str)
    assert sample_master_cv.full_name in formatted
    assert sample_master_cv.email in formatted
    # Check work experience is included
    assert sample_master_cv.work_experience[0].company in formatted


def test_format_cv_for_prompt_excludes_internal_ids(sample_master_cv):
    """Test formatted CV doesn't include internal IDs."""
    # Act
    formatted = format_cv_for_prompt(sample_master_cv)

    # Assert
    assert sample_master_cv.cv_id not in formatted
    assert sample_master_cv.user_id not in formatted


def test_format_job_description(sample_job_description):
    """Test job description formatting."""
    # Act
    formatted = format_job_description(sample_job_description)

    # Assert
    assert isinstance(formatted, str)
    assert len(formatted) > 0
    # Check original content is preserved
    assert "Python" in formatted


def test_annotate_with_relevance_scores(sample_master_cv, sample_relevance_scores):
    """Test CV sections are annotated with relevance scores."""
    # Act
    annotated = annotate_with_relevance_scores(
        cv_text=format_cv_for_prompt(sample_master_cv),
        relevance_scores=sample_relevance_scores,
    )

    # Assert
    assert isinstance(annotated, str)
    # Check annotations are present
    for section, score in sample_relevance_scores.items():
        if score > 0.7:
            assert f"{int(score * 100)}" in annotated or f"{score:.1f}" in annotated


def test_include_fvs_constraints(sample_fvs_baseline):
    """Test FVS constraints are formatted correctly."""
    # Act
    constraints = include_fvs_constraints(sample_fvs_baseline)

    # Assert
    assert isinstance(constraints, str)
    assert len(constraints) > 0
    assert "immutable" in constraints.lower() or "must not" in constraints.lower()


def test_include_fvs_constraints_lists_critical_facts(sample_fvs_baseline):
    """Test FVS constraints list critical facts."""
    # Act
    constraints = include_fvs_constraints(sample_fvs_baseline)

    # Assert
    # Check employment dates are listed
    date_facts = [
        f
        for f in sample_fvs_baseline.immutable_facts
        if f.fact_type == "employment_date"
    ]
    assert any(fact.value in constraints for fact in date_facts)


def test_include_keyword_targets(sample_keyword_list):
    """Test keyword targets are formatted."""
    # Act
    targets = include_keyword_targets(sample_keyword_list)

    # Assert
    assert isinstance(targets, str)
    assert all(keyword in targets for keyword in sample_keyword_list[:5])


def test_format_preferences(sample_tailoring_preferences):
    """Test preferences are formatted as instructions."""
    # Act
    formatted = format_preferences(sample_tailoring_preferences)

    # Assert
    assert isinstance(formatted, str)
    assert sample_tailoring_preferences.tone in formatted
    assert sample_tailoring_preferences.target_length.replace("_", " ") in formatted
    # Check emphasis areas
    assert any(
        area in formatted for area in sample_tailoring_preferences.emphasis_areas
    )


def test_build_prompt_complete_integration(
    sample_master_cv,
    sample_job_description,
    sample_relevance_scores,
    sample_fvs_baseline,
    sample_keyword_list,
    sample_tailoring_preferences,
):
    """Test complete prompt construction with all components."""
    # Act
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        relevance_scores=sample_relevance_scores,
        fvs_baseline=sample_fvs_baseline,
        target_keywords=sample_keyword_list,
        preferences=sample_tailoring_preferences,
    )

    # Assert
    assert len(system_prompt) > 100
    assert len(user_prompt) > 500
    # Check all components present in user prompt
    assert sample_master_cv.full_name in user_prompt
    assert "Python" in user_prompt  # From job description
    assert "relevance" in user_prompt.lower()
    assert "immutable" in user_prompt.lower()
    assert any(kw in user_prompt for kw in sample_keyword_list)
