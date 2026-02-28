# Live Tests - Gap Analysis Endpoints
# Tests: POST /jobs/{jobId}/gap-questions, POST /jobs/{jobId}/gap-responses, GET /jobs/{jobId}/gap-questions

import os
import json
import pytest
import requests
from typing import Dict, Any, List

# Import configuration
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .conftest import API_BASE, TEST_USER_ID, get_auth_headers, save_test_ids

# Import test data from previous tests
from .test_01_auth_health import test_data


def print_response(test_name: str, endpoint: str, status_code: int, response_data: Any):
    """Print JSON response for documentation."""
    output = {
        "test_name": test_name,
        "endpoint": endpoint,
        "status_code": status_code,
        "response": response_data,
    }
    print(f"\n=== RESPONSE {test_name} ===")
    print(json.dumps(output, indent=2, default=str))


class TestGapAnalysisEndpoints:
    """Test Gap Analysis endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE
        self.generated_questions: List[Dict] = []

    def test_generate_gap_questions(self):
        """Test POST /jobs/{jobId}/gap-questions - generate gap analysis questions."""
        # Build payload using test data
        cv_id = test_data.get("cv_id") or f"cv_{TEST_USER_ID}"
        job_id = test_data.get("job_id") or f"job_{TEST_USER_ID}"

        url = f"{self.base_url}/jobs/{job_id}/gap-questions"
        headers = get_auth_headers()

        payload = {
            "cv_id": cv_id,
            "max_questions": 10,
            "focus_areas": ["technical", "leadership", "achievements"],
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)

        # Accept 200 (success) or 400/422 (validation error)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_gap_questions",
                f"POST /jobs/{job_id}/gap-questions",
                response.status_code,
                data,
            )

            questions = data.get("questions", [])
            self.generated_questions = questions
            test_data["gap_questions"] = questions

            # Extract question IDs for response submission
            question_ids = [q.get("id") for q in questions if q.get("id")]
            test_data["gap_response_ids"] = question_ids
            save_test_ids(test_data)

            print(
                f"✓ POST /jobs/{job_id}/gap-questions - Generated {len(questions)} questions"
            )
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_generate_gap_questions",
                f"POST /jobs/{job_id}/gap-questions",
                response.status_code,
                data,
            )
            print(
                f"⚠ POST /jobs/{job_id}/gap-questions - Status {response.status_code}: {response.text[:200]}"
            )

    def test_submit_gap_responses(self):
        """Test POST /jobs/{jobId}/gap-responses - submit gap analysis responses."""
        # Get job ID from test data
        job_id = test_data.get("job_id") or f"job_{TEST_USER_ID}"

        url = f"{self.base_url}/jobs/{job_id}/gap-responses"
        headers = get_auth_headers()

        # Use generated questions or fallback
        questions = test_data.get("gap_questions", [])

        if not questions:
            # Create sample responses
            responses = [
                {
                    "question_id": f"gap_q_{i + 1}",
                    "response": f"Test response for question {i + 1}. I led a team of 8 engineers to migrate our legacy monolith to microservices, reducing deployment time by 60%.",
                    "quantifiable_data": {
                        "team_size": 8,
                        "duration_months": 12,
                        "percentage": 60,
                    },
                }
                for i in range(3)
            ]
        else:
            # Use first 3 questions
            responses = []
            for q in questions[:3]:
                responses.append(
                    {
                        "question_id": q.get("id", f"gap_q_{questions.index(q) + 1}"),
                        "response": f"Test response for: {q.get('text', 'Sample question')[:50]}... Led a team of 8 engineers to migrate our legacy monolith to microservices.",
                        "quantifiable_data": {
                            "team_size": 8,
                            "duration_months": 12,
                            "percentage": 60,
                        },
                    }
                )

        payload = {"responses": responses}

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        # Accept 200 (success) or 400/422 (validation error)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_submit_gap_responses",
                f"POST /jobs/{job_id}/gap-responses",
                response.status_code,
                data,
            )

            impact_statements = data.get("impact_statements", [])
            print(
                f"✓ POST /jobs/{job_id}/gap-responses - Submitted {len(responses)} responses, got {len(impact_statements)} impact statements"
            )
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_submit_gap_responses",
                f"POST /jobs/{job_id}/gap-responses",
                response.status_code,
                data,
            )
            print(
                f"⚠ POST /jobs/{job_id}/gap-responses - Status {response.status_code}: {response.text[:200]}"
            )

    def test_get_gap_questions(self):
        """Test GET /jobs/{jobId}/gap-questions - get previous gap questions."""
        job_id = test_data.get("job_id") or f"job_{TEST_USER_ID}"

        url = f"{self.base_url}/jobs/{job_id}/gap-questions"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        # Accept 200 (success), 404 (not found), or 401 (auth required)
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_get_gap_questions",
                f"GET /jobs/{job_id}/gap-questions",
                response.status_code,
                data,
            )

            questions = data.get("questions", [])
            print(
                f"✓ GET /jobs/{job_id}/gap-questions - Found {len(questions)} questions"
            )
        elif response.status_code == 404:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_get_gap_questions",
                f"GET /jobs/{job_id}/gap-questions",
                response.status_code,
                data,
            )
            print(
                f"⚠ GET /jobs/{job_id}/gap-questions - No questions found for job"
            )
        else:
            try:
                data = response.json()
            except Exception:
                data = {"raw_text": response.text}

            print_response(
                "test_get_gap_questions",
                f"GET /jobs/{job_id}/gap-questions",
                response.status_code,
                data,
            )
            print(
                f"⚠ GET /jobs/{job_id}/gap-questions - Status {response.status_code}"
            )
