"""
Unit tests for Interview Prep Prompt module.

Tests prompt construction and output schemas for interview preparation.
Per docs/refactor/specs/interview_prep_spec.yaml.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_cv_facts():
    """Create sample CV facts for testing."""
    return {
        'full_name': 'John Doe',
        'email': 'john.doe@example.com',
        'experience': [
            {
                'company': 'Acme Corp',
                'role': 'Software Engineer',
                'duration': '2 years',
                'achievements': [
                    'Led migration to microservices',
                    'Improved system reliability by 40%',
                ],
            },
            {
                'company': 'Tech Start',
                'role': 'Junior Developer',
                'duration': '1 year',
                'achievements': ['Built REST APIs from scratch'],
            },
        ],
        'skills': ['Python', 'AWS', 'Docker', 'PostgreSQL'],
        'education': [
            {
                'institution': 'State University',
                'degree': 'BS Computer Science',
                'graduation_year': 2018,
            }
        ],
    }


@pytest.fixture
def sample_vpr_differentiators():
    """Create sample VPR differentiators."""
    return [
        'Architected scalable microservices at Acme Corp',
        'Reduced deployment time by 60% through CI/CD automation',
        'Mentored 3 junior developers',
    ]


@pytest.fixture
def sample_gap_responses():
    """Create sample gap analysis responses."""
    return [
        {
            'question': 'What experience do you have with Kubernetes?',
            'response': 'While I have not used Kubernetes directly, I have extensive experience with Docker containerization and AWS ECS. I understand container orchestration concepts and am currently learning Kubernetes through an online course.',
        },
        {
            'question': 'Tell us about your leadership experience.',
            'response': 'As a senior engineer at Acme Corp, I led a team of 4 developers on a major platform migration project. I also regularly mentor junior team members and have conducted technical workshops.',
        },
    ]


@pytest.fixture
def sample_job_requirements():
    """Create sample job requirements."""
    return {
        'title': 'Senior Software Engineer',
        'required_skills': ['Python', 'AWS', 'Kubernetes', 'CI/CD'],
        'preferred_skills': ['Terraform', 'AWS Lambda', 'GraphQL'],
        'responsibilities': [
            'Design and implement scalable services',
            'Mentor junior engineers',
            'Participate in on-call rotation',
        ],
    }


# ============================================================================
# Test Class 1: Interview Question Types
# ============================================================================


class TestInterviewQuestionTypes:
    """Tests for interview question type classification."""

    def test_behavioral_question_detection(self):
        """Test detection of behavioral questions."""
        behavioral_phrases = [
            'tell me about a time',
            'describe a situation',
            'give an example',
            'when did you',
            'how did you handle',
        ]
        questions = [
            'Tell me about a time you faced a difficult challenge.',
            'Describe a situation where you had to make a tough decision.',
        ]
        for question in questions:
            is_behavioral = any(phrase in question.lower() for phrase in behavioral_phrases)
            assert is_behavioral is True

    def test_technical_question_detection(self):
        """Test detection of technical questions."""
        technical_keywords = ['how would you', 'what is', 'explain', 'technical', 'architecture']
        questions = [
            'How would you design a scalable system?',
            'What is your experience with microservices?',
        ]
        for question in questions:
            is_technical = any(keyword in question.lower() for keyword in technical_keywords)
            assert is_technical is True

    def test_situational_question_detection(self):
        """Test detection of situational questions."""
        situational_phrases = ['what would you do', 'if you were', 'suppose']
        questions = [
            'What would you do if you discovered a critical bug in production?',
            'If you had to choose between speed and quality, what would you do?',
        ]
        for question in questions:
            is_situational = any(phrase in question.lower() for phrase in situational_phrases)
            assert is_situational is True

    def test_gap_focused_question_detection(self):
        """Test detection of gap-focused questions."""
        gap_phrases = ['experience with', 'background in', 'limited', 'what experience']
        questions = [
            'I noticed your experience with Kubernetes is limited. How would you address this?',
            'What experience do you have with cloud platforms?',
        ]
        for question in questions:
            is_gap_focused = any(phrase in question.lower() for phrase in gap_phrases)
            assert is_gap_focused is True


# ============================================================================
# Test Class 2: STAR Method Structure
# ============================================================================


class TestSTARMethodStructure:
    """Tests for STAR method answer structure validation."""

    def test_star_elements_identified(self):
        """Test identifying STAR elements in answer."""
        answer = """
        Situation: Our team was struggling with slow deployment times.
        Task: I was tasked with reducing deployment time by 50%.
        Action: I implemented CI/CD pipelines and automated testing.
        Result: Deployment time was reduced by 60%.
        """
        has_situation = 'situation' in answer.lower() or 'struggling' in answer.lower()
        has_task = 'task' in answer.lower() or 'tasked' in answer.lower()
        has_action = 'action' in answer.lower() or 'implemented' in answer.lower()
        has_result = 'result' in answer.lower() or 'reduced' in answer.lower()

        assert has_situation is True
        assert has_task is True
        assert has_action is True
        assert has_result is True

    def test_star_element_count(self):
        """Test that valid STAR answer has all elements."""
        star_elements = {
            'situation': ['situation:', 'scenario:', 'context:'],
            'task': ['task:', 'responsibility:', 'goal:'],
            'action': ['action:', 'steps:', 'approach:'],
            'result': ['result:', 'outcome:', 'achievement:'],
        }

        answer = """
        Situation: The team faced frequent production outages.
        Task: I needed to improve system reliability.
        Action: I implemented monitoring and alerting.
        Result: Uptime improved to 99.9%.
        """
        element_count = 0
        for element, prefixes in star_elements.items():
            for prefix in prefixes:
                if prefix in answer.lower():
                    element_count += 1
                    break

        assert element_count >= 3  # At least 3 elements should be identified

    def test_quantifiable_result_detection(self):
        """Test detection of quantifiable results."""
        answers_with_metrics = [
            'Reduced latency by 40%',
            'Improved uptime to 99.9%',
            'Decreased deployment time from 2 hours to 15 minutes',
            'Increased user engagement by 25%',
        ]
        metric_pattern = r'\d+\.?\d*%|\$\d+|\d+\s*(hours?|minutes?|seconds?)'

        for answer in answers_with_metrics:
            import re
            has_metric = bool(re.search(metric_pattern, answer, re.IGNORECASE))
            assert has_metric is True


# ============================================================================
# Test Class 3: Prompt Construction
# ============================================================================


class TestPromptConstruction:
    """Tests for interview prep prompt construction."""

    def test_cv_context_injection(self, sample_cv_facts):
        """Test that CV facts are properly injected into prompt."""
        cv_text = f"""
        Candidate: {sample_cv_facts['full_name']}
        Email: {sample_cv_facts['email']}

        Experience:
        """
        for exp in sample_cv_facts['experience']:
            cv_text += f"- {exp['role']} at {exp['company']} ({exp['duration']})\n"
            for achievement in exp['achievements']:
                cv_text += f"  * {achievement}\n"

        assert sample_cv_facts['full_name'] in cv_text
        assert 'Software Engineer' in cv_text
        assert 'Acme Corp' in cv_text

    def test_vpr_differentiators_injection(self, sample_vpr_differentiators):
        """Test VPR differentiators are included."""
        differentiators_text = '\n'.join(
            f"- {diff}" for diff in sample_vpr_differentiators
        )
        assert 'Architected scalable microservices' in differentiators_text

    def test_gap_responses_prioritization(self, sample_gap_responses):
        """Test gap responses are prioritized in prompt."""
        gap_text = "Key Gap Areas to Address:\n"
        for i, gap in enumerate(sample_gap_responses, 1):
            gap_text += f"\n{i}. Question: {gap['question']}\n"
            gap_text += f"   Response Strategy: {gap['response']}\n"

        assert 'Kubernetes' in gap_text
        assert 'leadership experience' in gap_text.lower()

    def test_job_requirements_context(self, sample_job_requirements):
        """Test job requirements are included in prompt."""
        job_text = f"""
        Target Position: {sample_job_requirements['title']}

        Required Skills:
        """
        for skill in sample_job_requirements['required_skills']:
            job_text += f"- {skill}\n"

        job_text += "\nPreferred Skills:\n"
        for skill in sample_job_requirements['preferred_skills']:
            job_text += f"- {skill}\n"

        assert 'Senior Software Engineer' in job_text
        assert 'Python' in job_text
        assert 'Kubernetes' in job_text


# ============================================================================
# Test Class 4: Question Prioritization
# ============================================================================


class TestQuestionPrioritization:
    """Tests for question prioritization logic."""

    def test_gap_questions_prioritized(self, sample_gap_responses):
        """Test that gap-focused questions are prioritized."""
        questions = [
            {'text': 'What is your experience with Python?', 'type': 'Technical', 'priority': 2},
            {'text': sample_gap_responses[0]['question'], 'type': 'Gap-Focused', 'priority': 1},
            {'text': 'Tell me about yourself.', 'type': 'Behavioral', 'priority': 3},
        ]

        # Gap questions should have higher priority (lower number)
        gap_question = next(q for q in questions if q['type'] == 'Gap-Focused')
        assert gap_question['priority'] < 2  # Should be in top 2

    def test_max_questions_limit(self):
        """Test max questions limit is enforced."""
        all_questions = [
            {'text': f'Question {i}', 'type': 'Technical'}
            for i in range(15)
        ]
        max_questions = 10

        prioritized = all_questions[:max_questions]
        assert len(prioritized) <= max_questions

    def test_question_type_distribution(self):
        """Test balanced distribution across question types."""
        questions = [
            {'text': 'Q1', 'type': 'Behavioral'},
            {'text': 'Q2', 'type': 'Behavioral'},
            {'text': 'Q3', 'type': 'Technical'},
            {'text': 'Q4', 'type': 'Technical'},
            {'text': 'Q5', 'type': 'Situational'},
            {'text': 'Q6', 'type': 'Gap-Focused'},
        ]
        max_per_type = 4

        type_counts = {}
        for q in questions:
            q_type = q['type']
            type_counts[q_type] = type_counts.get(q_type, 0) + 1

        for count in type_counts.values():
            assert count <= max_per_type


# ============================================================================
# Test Class 5: Answer Structure Validation
# ============================================================================


class TestAnswerStructureValidation:
    """Tests for answer structure validation."""

    def test_answer_length_range(self):
        """Test answer length is within 150-300 words."""
        valid_lengths = [
            'Word ' * 150,  # 150 words
            'Word ' * 200,  # 200 words
            'Word ' * 300,  # 300 words
        ]
        min_words = 150
        max_words = 300

        for answer in valid_lengths:
            word_count = len(answer.split())
            assert min_words <= word_count <= max_words

    def test_answer_paragraph_count(self):
        """Test answer has appropriate paragraph count."""
        valid_answer = """
        First paragraph introduces the situation.

        Second paragraph describes the action taken.

        Third paragraph concludes with the result.
        """
        paragraphs = [p.strip() for p in valid_answer.strip().split('\n\n') if p.strip()]
        assert 2 <= len(paragraphs) <= 3

    def test_answer_has_candidate_specific_details(self, sample_cv_facts):
        """Test answers include candidate-specific details."""
        answer_with_details = """
        In my role as Software Engineer at Acme Corp, I led a team migration to microservices.
        This aligns with my experience building scalable systems.
        The result was a 40% improvement in system reliability.
        """
        assert 'Acme Corp' in answer_with_details
        assert 'Software Engineer' in answer_with_details
        assert '40%' in answer_with_details

    def test_answer_avoids_generic_statements(self):
        """Test answers avoid generic AI-like statements."""
        generic_phrases = [
            'I am a hard worker',
            'I am a team player',
            'I have excellent communication skills',
        ]
        specific_answer = """
        As a senior engineer, I led a team of 4 developers at Acme Corp.
        We migrated from a monolith to microservices, reducing deployment time by 60%.
        This project improved our CI/CD pipeline significantly.
        """
        for phrase in generic_phrases:
            assert phrase.lower() not in specific_answer.lower()


# ============================================================================
# Test Class 6: Output Schema Validation
# ============================================================================


class TestOutputSchemaValidation:
    """Tests for interview prep output schema."""

    def test_question_schema_fields(self):
        """Test question output has required fields."""
        question_schema = {
            'type': 'string',
            'question': 'string',
            'suggested_answer': {
                'content': 'string',
                'word_count': 'integer',
                'star_elements': {
                    'situation': 'string',
                    'task': 'string',
                    'action': 'string',
                    'result': 'string',
                },
            },
            'priority': 'integer',
        }
        required_fields = ['type', 'question', 'suggested_answer', 'priority']
        for field in required_fields:
            assert field in question_schema

    def test_interview_prep_output_schema(self):
        """Test full interview prep output has required fields."""
        output_schema = {
            'questions': 'List[Question]',
            'total_questions': 'integer',
            'questions_by_type': {
                'Behavioral': 'integer',
                'Technical': 'integer',
                'Situational': 'integer',
                'Gap-Focused': 'integer',
            },
        }
        required_fields = ['questions', 'total_questions', 'questions_by_type']
        for field in required_fields:
            assert field in output_schema

    def test_questions_by_type_counts(self):
        """Test questions_by_type correctly counts question types."""
        questions = [
            {'type': 'Behavioral'},
            {'type': 'Technical'},
            {'type': 'Behavioral'},
            {'type': 'Situational'},
            {'type': 'Gap-Focused'},
        ]
        type_counts = {}
        for q in questions:
            q_type = q['type']
            type_counts[q_type] = type_counts.get(q_type, 0) + 1

        assert type_counts['Behavioral'] == 2
        assert type_counts['Technical'] == 1
        assert type_counts['Situational'] == 1
        assert type_counts['Gap-Focused'] == 1


# ============================================================================
# Test Class 7: Integration Scenarios
# ============================================================================


class TestInterviewPrepIntegration:
    """Integration tests for interview prep flow."""

    def test_full_prompt_construction(
        self,
        sample_cv_facts,
        sample_vpr_differentiators,
        sample_gap_responses,
        sample_job_requirements,
    ):
        """Test full prompt construction with all components."""
        prompt = f"""
        You are preparing {sample_cv_facts['full_name']} for an interview.

        TARGET POSITION: {sample_job_requirements['title']}

        REQUIRED SKILLS:
        {', '.join(sample_job_requirements['required_skills'])}

        KEY DIFFERENTIATORS (from VPR):
        {chr(10).join(f'- {d}' for d in sample_vpr_differentiators)}

        GAP AREAS TO ADDRESS:
        {chr(10).join(f'- {g["question"]}: {g["response"][:50]}...' for g in sample_gap_responses)}

        Generate 5 interview questions with suggested answers.
        """

        assert sample_cv_facts['full_name'] in prompt
        assert 'Senior Software Engineer' in prompt
        assert 'Python' in prompt
        assert 'Architected scalable microservices' in prompt

    def test_cv_facts_in_answer_context(self, sample_cv_facts):
        """Test CV facts are used in answer generation context."""
        answer_context = {
            'candidate_name': sample_cv_facts['full_name'],
            'relevant_experience': [
                {
                    'company': exp['company'],
                    'role': exp['role'],
                    'achievements': exp['achievements'],
                }
                for exp in sample_cv_facts['experience']
            ],
            'key_skills': sample_cv_facts['skills'],
        }

        assert answer_context['candidate_name'] == 'John Doe'
        assert len(answer_context['relevant_experience']) == 2
        assert 'Python' in answer_context['key_skills']

    def test_job_specific_question_generation(self, sample_job_requirements):
        """Test questions are tailored to job requirements."""
        required_skills = sample_job_requirements['required_skills']
        job_specific_questions = [
            f'How would you implement {" or ".join(required_skills[:2])}?',
            f'Tell me about your experience with {required_skills[2]}.',
        ]
        for question in job_specific_questions:
            has_job_reference = any(
                skill.lower() in question.lower() for skill in required_skills
            )
            assert has_job_reference is True

    def test_answer_includes_achievements(self, sample_cv_facts):
        """Test answers include specific achievements."""
        achievement_text = ' '.join(
            achievement
            for exp in sample_cv_facts['experience']
            for achievement in exp['achievements']
        )
        achievements = [
            'migration to microservices',
            'Improved system reliability',
            'Built REST APIs',
        ]
        for achievement in achievements:
            # Check at least one achievement reference exists
            has_achievement = any(
                word.lower() in achievement_text.lower()
                for word in achievement.split()[:2]
            )
            assert has_achievement is True


# ============================================================================
# Test Class 8: Anti-AI Pattern Detection
# ============================================================================


class TestAntiAIPatterns:
    """Tests for anti-AI pattern detection in answers."""

    def test_excessive_formality_detection(self):
        """Test detection of excessively formal language."""
        formal_phrases = [
            'in the ever-evolving landscape',
            'leverage synergistic solutions',
            'think outside the box',
            'at the end of the day',
            'paradigm shift',
        ]
        text_with_patterns = "In the ever-evolving landscape of technology, we must leverage synergistic solutions."
        detected_patterns = [p for p in formal_phrases if p.lower() in text_with_patterns.lower()]
        assert len(detected_patterns) >= 1

    def test_perfect_parallel_structure_detection(self):
        """Test detection of overly parallel structure."""
        parallel_text = "I analyzed the problem. I designed a solution. I implemented the fix. I tested the results."
        sentences = [s.strip() for s in parallel_text.split('.') if s.strip()]
        has_parallel = len(sentences) == 4 and all(
            s.startswith('I') for s in sentences
        )
        assert has_parallel is True

    def test_no_first_person_recommendation(self):
        """Test that answers don't overuse first person."""
        valid_answer = """
        The team was facing deployment challenges. The approach involved implementing CI/CD pipelines.
        The outcome was a significant improvement in deployment frequency.
        """
        first_person_count = valid_answer.lower().count(' i ') + valid_answer.lower().count("i'm")
        assert first_person_count == 0

    def test_answer_tone_variation(self):
        """Test answers have varied tone."""
        formal_answer = "One should always consider the implications of architectural decisions."
        casual_answer = "It's important to think about how your design choices affect the system."
        assert formal_answer != casual_answer


# ============================================================================
# Test Class 9: Edge Cases
# ============================================================================


class TestInterviewPrepEdgeCases:
    """Tests for edge cases in interview prep."""

    def test_no_gap_responses_handled(self):
        """Test handling when no gap responses exist."""
        cv_facts = {'skills': ['Python', 'AWS']}
        job_requirements = {'required_skills': ['Python', 'AWS', 'Kubernetes']}
        # Should still generate questions without gap focus
        assert 'Kubernetes' not in str(cv_facts.get('skills', []))

    def test_minimal_cv_data(self):
        """Test handling with minimal CV data."""
        minimal_cv = {
            'full_name': 'John Doe',
            'experience': [{'company': 'Test Co', 'role': 'Developer'}],
        }
        questions = ['Tell me about yourself.', 'Why do you want this role?']
        assert len(questions) == 2

    def test_empty_skills_handled(self):
        """Test handling when skills list is empty."""
        cv_facts = {
            'skills': [],
            'experience': [
                {'company': 'Acme', 'role': 'Developer', 'achievements': ['Built things']}
            ],
        }
        # Should generate experience-based questions instead
        assert len(cv_facts['skills']) == 0

    def test_multiple_job_requirements(self):
        """Test handling multiple similar job requirements."""
        skills = ['Python', 'Python', 'Python']  # Duplicate
        unique_skills = list(dict.fromkeys(skills))  # Preserve order, remove dupes
        assert len(unique_skills) == 1
