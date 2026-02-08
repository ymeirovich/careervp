"""
End-to-end test for CV Tailoring feature deployed on AWS.

This test verifies:
1. CV Upload endpoint works
2. CV Tailoring endpoint returns tailored CV directly in response

Usage:
    python cv_tailoring_e2e_test.py [--api-url URL] [--cv-id CV_ID] [--user-id USER_ID]

Environment variables:
    API_URL       - API Gateway URL (default: auto-detect from CloudFormation)
    CV_ID         - CV ID to use for testing (auto-generated if not provided)
    USER_ID       - User ID for authentication
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Any

import boto3
import requests


# Sample CV as plain text (for upload via text_content)
SAMPLE_CV_TEXT = """
Yitzchak Meirovitch
yitzchak@example.com | +972-50-123-4567 | Tel Aviv, Israel

Professional Summary:
Senior Software Engineer with 8+ years of experience in full-stack development, specializing in Python, AWS, and building scalable web applications.

Work Experience:

TechCorp Israel | Senior Software Engineer | Jan 2020 - Present
- Leading development of cloud-native microservices using Python and AWS
- Reduced API latency by 40% through optimization
- Mentored 5 junior engineers
- Implemented CI/CD pipeline reducing deployment time by 60%
- Technologies: Python, AWS, Docker, Kubernetes, PostgreSQL

StartupIL | Software Engineer | Jun 2017 - Dec 2019
- Developed RESTful APIs and frontend features for a fintech startup
- Built payment processing system handling $1M+ monthly transactions
- Improved test coverage from 40% to 85%
- Technologies: Python, React, Node.js, PostgreSQL, Redis

Education:
Tel Aviv University | Bachelor of Science, Computer Science | 2013-2017
GPA: 3.7 | Dean's List

Skills:
Python (EXPERT, 8 years), AWS (ADVANCED, 5 years), Docker (ADVANCED, 4 years),
Kubernetes (ADVANCED, 3 years), PostgreSQL (ADVANCED, 5 years), React (INTERMEDIATE, 3 years)

Certifications:
AWS Certified Solutions Architect | Amazon Web Services | Jan 2023 - Jan 2026

Languages:
English (Native), Hebrew (Native)
"""


# Sample job description for testing
JOB_DESCRIPTION = """
Senior Python Developer - Cloud Infrastructure

We are seeking an experienced Senior Python Developer to join our cloud infrastructure team.
The ideal candidate will have strong expertise in Python development, AWS cloud services,
and containerization technologies.

Key Responsibilities:
- Design and implement scalable microservices using Python and FastAPI
- Manage AWS infrastructure using Infrastructure as Code (Terraform, CDK)
- Build and maintain CI/CD pipelines for automated deployment
- Optimize application performance and reduce latency
- Mentor junior developers and conduct code reviews
- Collaborate with cross-functional teams to deliver features

Required Skills:
- 5+ years of professional Python development experience
- Strong knowledge of AWS services (Lambda, ECS, S3, DynamoDB)
- Experience with Docker and Kubernetes
- Proficiency in SQL and NoSQL databases (PostgreSQL, DynamoDB)
- Understanding of microservices architecture and RESTful APIs
- Experience with version control systems (Git)

Preferred Qualifications:
- AWS certifications (Solutions Architect, Developer)
- Experience with FastAPI or Flask frameworks
- Knowledge of monitoring tools (CloudWatch, DataDog)
- Familiarity with event-driven architectures
- Experience mentoring junior engineers

What We Offer:
- Competitive salary and equity package
- Remote-first work environment
- Professional development budget
- Health, dental, and vision insurance
- 401(k) matching

About Us:
We're a fast-growing startup building the next generation of cloud infrastructure tools.
Our team values innovation, collaboration, and continuous learning.
"""


def get_api_url_from_cloudformation(stack_name: str = "CareerVpCrudDev") -> str:
    """Get API URL from CloudFormation stack outputs."""
    client = boto3.client("cloudformation", region_name="us-east-1")
    try:
        response = client.describe_stacks(StackName=stack_name)
        for output in response["Stacks"][0]["Outputs"]:
            if output["OutputKey"] == "Apigateway":
                return output["OutputValue"]
    except Exception as e:
        print(f"Warning: Could not get API URL from CloudFormation: {e}")
    return ""


def normalize_url(url: str) -> str:
    """Normalize URL by removing trailing slashes and duplicate slashes."""
    # Remove trailing slash
    url = url.rstrip("/")
    # Fix double slashes (e.g., "prod//api" -> "prod/api")
    url = url.replace("//", "/").replace(":/", "://")
    return url


def wait_for_deployment(
    api_url: str, max_retries: int = 30, delay: float = 5.0
) -> bool:
    """Wait for the API to be available after deployment."""
    api_url = normalize_url(api_url)
    # Test the swagger endpoint which should always work
    test_url = f"{api_url}/swagger"

    print(f"Waiting for API to be available at {test_url}...")

    for attempt in range(max_retries):
        try:
            response = requests.get(test_url, timeout=10)
            if response.status_code in [200, 404, 405, 502]:
                print(f"API is responding (status: {response.status_code})")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except requests.exceptions.Timeout:
            pass

        print(f"  Attempt {attempt + 1}/{max_retries}...")
        time.sleep(delay)

    return False


def test_cv_upload(api_url: str, cv_text: str, user_id: str) -> tuple[bool, str]:
    """
    Upload a CV using POST /api/cv with text_content.
    Returns (success, cv_id).
    """
    api_url = normalize_url(api_url)
    endpoint = "/api/cv"
    url = f"{api_url}{endpoint}"

    # Generate unique CV ID
    cv_id = f"test-cv-{uuid.uuid4().hex[:8]}"

    payload = {"cv_id": cv_id, "user_id": user_id, "text_content": cv_text}

    print(f"\nTest: CV Upload")
    print(f"  URL: {url}")
    print(f"  CV ID: {cv_id}")
    print(f"  Text Content Length: {len(cv_text)} chars")

    try:
        response = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}, timeout=60
        )
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"  Response keys: {list(data.keys())}")
            print(f"  Success field: {data.get('success')}")
            # CV upload returns "user_cv" with cv_id inside
            if data.get("success") and data.get("user_cv"):
                user_cv = data["user_cv"]
                if isinstance(user_cv, dict):
                    returned_cv_id = user_cv.get("cv_id") or cv_id
                else:
                    returned_cv_id = cv_id
                print(f"  Extracted CV ID: {returned_cv_id}")
                return True, returned_cv_id
            else:
                print(f"  Response: {data}")
                return True, cv_id  # Still return the cv_id we used
        else:
            print(f"  Error: {response.text[:200]}")
            return False, cv_id

    except Exception as e:
        print(f"  Error: {e}")
        return False, cv_id


def test_cv_tailoring(
    api_url: str,
    cv_id: str,
    job_description: str,
    user_id: str,
    preferences: dict[str, Any] | None = None,
) -> bool:
    """
    Test CV tailoring using POST /api/cv-tailoring.
    Returns the tailored CV directly in the response.
    """
    api_url = normalize_url(api_url)
    endpoint = "/api/cv-tailoring"
    url = f"{api_url}{endpoint}"

    payload = {"cv_id": cv_id, "job_description": job_description, "user_id": user_id}

    if preferences:
        payload["preferences"] = preferences

    print(f"\nTest: CV Tailoring")
    print(f"  URL: {url}")
    print(f"  CV ID: {cv_id}")
    print(f"  Job Description Length: {len(job_description)} chars")

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120,  # LLM can take time
        )
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"  Success: {data.get('success')}")

            if data.get("success"):
                # CV Tailoring returns tailored CV DIRECTLY in response
                tailored_cv = data.get("data", {}).get("tailored_cv")
                if tailored_cv:
                    print(f"  Tailored CV received: Yes")
                    print(
                        f"  Tailored Summary: {tailored_cv.get('professional_summary', '')[:150]}..."
                    )
                    # Print full tailored CV JSON
                    print(f"\n  === FULL TAILORED CV ===")
                    print(json.dumps(tailored_cv, indent=2))
                    print(f"  === END TAILORED CV ===\n")
                    return True
                else:
                    print(f"  Error: No tailored_cv in response")
                    print(f"  Response data keys: {list(data.get('data', {}).keys())}")
                    return False
            else:
                print(f"  Error: {data.get('message', 'Unknown error')}")
                return False
        elif response.status_code == 400:
            print(
                f"  Bad Request: {response.json().get('message', 'Validation error')}"
            )
            return False
        elif response.status_code == 401:
            print(f"  Unauthorized: Missing or invalid authentication")
            return False
        elif response.status_code == 404:
            print(f"  Not Found: CV not found (cv_id={cv_id})")
            return False
        elif response.status_code == 429:
            print(f"  Rate Limited: Too many requests")
            return False
        elif response.status_code == 500:
            print(f"  Server Error: {response.json().get('message', 'Internal error')}")
            return False
        else:
            print(f"  Unexpected status: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print(f"  Error: Request timed out (LLM may be processing)")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def test_cv_tailoring_with_preferences(
    api_url: str, cv_id: str, job_description: str, user_id: str
) -> bool:
    """Test CV tailoring with custom preferences."""
    api_url = normalize_url(api_url)
    endpoint = "/api/cv-tailoring"
    url = f"{api_url}{endpoint}"

    preferences = {
        "tone": "professional",
        "target_length": "one_page",
        "emphasis_areas": ["python", "aws", "cloud_infrastructure"],
    }

    payload = {
        "cv_id": cv_id,
        "job_description": job_description,
        "user_id": user_id,
        "preferences": preferences,
    }

    print(f"\nTest: CV Tailoring with Preferences")
    print(f"  URL: {url}")
    print(f"  Preferences: {preferences}")

    try:
        response = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}, timeout=120
        )
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                tailored_cv = data.get("data", {}).get("tailored_cv")
                if tailored_cv:
                    print(f"  Success: Tailored CV with preferences generated")
                    return True

        print(f"  Response: {response.json()}")
        return False

    except Exception as e:
        print(f"  Error: {e}")
        return False


def test_invalid_cv_id(api_url: str, user_id: str) -> bool:
    """Test that invalid CV ID returns appropriate error."""
    api_url = normalize_url(api_url)
    endpoint = "/api/cv-tailoring"
    url = f"{api_url}{endpoint}"

    payload = {
        "cv_id": "non-existent-cv",
        "job_description": "Looking for a Python developer",
        "user_id": user_id,
    }

    print(f"\nTest: Invalid CV ID")
    print(f"  URL: {url}")
    print(f"  CV ID: non-existent-cv")

    try:
        response = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}, timeout=30
        )
        print(f"  Status: {response.status_code}")

        # Handler returns 400 for invalid/non-existent user_id (since it fetches by user_id)
        if response.status_code in [400, 404]:
            print(f"  Correct: Returns error for non-existent user")
            return True
        else:
            print(f"  Unexpected response: {response.status_code}")
            return False

    except Exception as e:
        print(f"  Error: {e}")
        return False


def test_validation_error(api_url: str, user_id: str) -> bool:
    """Test that validation catches invalid input."""
    api_url = normalize_url(api_url)
    endpoint = "/api/cv-tailoring"
    url = f"{api_url}{endpoint}"

    payload = {
        "cv_id": "test-cv",
        "job_description": "Too short",  # Should fail validation
        "user_id": user_id,
    }

    print(f"\nTest: Validation Error")
    print(f"  URL: {url}")
    print(f"  Job Description: '{payload['job_description']}' (too short)")

    try:
        response = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}, timeout=30
        )
        print(f"  Status: {response.status_code}")

        if response.status_code == 400:
            data = response.json()
            if not data.get("success"):
                print(f"  Correct: Validation caught short job description")
                return True

        print(f"  Response: {response.json()}")
        return False

    except Exception as e:
        print(f"  Error: {e}")
        return False


def save_test_result(result_file: str, results: dict[str, Any]) -> None:
    """Save test results to a JSON file."""
    results["timestamp"] = datetime.now().isoformat()

    with open(result_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to: {result_file}")


def run_tests(api_url: str, user_id: str, save_results: bool = True) -> dict[str, Any]:
    """Run all E2E tests."""
    print("=" * 60)
    print("CV Tailoring E2E Test Suite")
    print("=" * 60)
    print(f"API URL: {api_url}")
    print(f"User ID: {user_id}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {
        "api_url": api_url,
        "user_id": user_id,
        "tests": {},
        "passed": 0,
        "failed": 0,
        "total": 0,
    }

    # Step 1: Upload a CV first
    print("\n" + "=" * 60)
    print("STEP 1: Upload CV")
    print("=" * 60)

    cv_upload_success, cv_id = test_cv_upload(api_url, SAMPLE_CV_TEXT, user_id)
    if cv_upload_success:
        print(f"  CV uploaded successfully with ID: {cv_id}")
    else:
        print(f"  ERROR: CV upload failed. Cannot proceed with tailoring tests.")
        results["tests"]["cv_upload"] = {"passed": False, "error": "CV upload failed"}
        results["total"] += 1
        results["failed"] += 1

        if save_results:
            save_test_result("cv_tailoring_e2e_results.json", results)

        return results

    # Step 2: Run CV Tailoring tests
    print("\n" + "=" * 60)
    print("STEP 2: CV Tailoring Tests")
    print("=" * 60)

    tests = [
        (
            "cv_tailoring_basic",
            lambda: test_cv_tailoring(api_url, cv_id, JOB_DESCRIPTION, user_id),
        ),
        (
            "cv_tailoring_with_preferences",
            lambda: test_cv_tailoring_with_preferences(
                api_url, cv_id, JOB_DESCRIPTION, user_id
            ),
        ),
        ("invalid_cv_id", lambda: test_invalid_cv_id(api_url, user_id)),
        ("validation_error", lambda: test_validation_error(api_url, user_id)),
    ]

    for test_name, test_func in tests:
        results["total"] += 1
        try:
            success = test_func()
            results["tests"][test_name] = {"passed": success, "error": None}
            if success:
                results["passed"] += 1
                print(f"  Result: PASSED")
            else:
                results["failed"] += 1
                print(f"  Result: FAILED")
        except Exception as e:
            results["tests"][test_name] = {"passed": False, "error": str(e)}
            results["failed"] += 1
            print(f"  Result: ERROR - {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Total: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Success Rate: {(results['passed'] / results['total'] * 100):.1f}%")

    if save_results:
        save_test_result("cv_tailoring_e2e_results.json", results)

    return results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="E2E tests for CV Tailoring feature on AWS"
    )
    parser.add_argument(
        "--api-url", default=os.environ.get("API_URL", ""), help="API Gateway URL"
    )
    parser.add_argument(
        "--cv-id",
        default="",
        help="Optional: CV ID to use (auto-generated if not provided)",
    )
    parser.add_argument(
        "--user-id",
        default=os.environ.get("USER_ID", "test-user-001"),
        help="User ID for authentication",
    )
    parser.add_argument(
        "--skip-health-wait", action="store_true", help="Skip waiting for deployment"
    )

    args = parser.parse_args()

    # Get API URL if not provided
    if not args.api_url:
        print("No API URL provided. Attempting to detect from CloudFormation...")
        args.api_url = get_api_url_from_cloudformation()

    if not args.api_url:
        print("Error: API URL is required. Provide --api-url or set API_URL env var.")
        return 1

    # Run tests
    results = run_tests(api_url=args.api_url, user_id=args.user_id)

    # Return exit code based on results
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
