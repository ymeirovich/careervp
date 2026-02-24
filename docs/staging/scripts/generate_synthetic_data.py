#!/usr/bin/env python3
"""
Synthetic Data Generator for Staging Environment

Generates realistic test data for the CareerVP staging environment including:
- Test users (job seekers with various profiles)
- Test jobs (various positions and companies)
- Test CVs (sample resumes in different formats)
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Constants
NUM_TEST_USERS = 10
NUM_TEST_JOBS = 20


def generate_test_users() -> list[dict[str, Any]]:
    """Generate synthetic test users."""
    first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa", "William", "Jennifer"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    countries = ["ISRAEL", "USA"]
    subscription_tiers = ["free", "premium", "trial"]

    users = []
    for i in range(NUM_TEST_USERS):
        user = {
            "user_id": str(uuid.uuid4()),
            "email": f"test.user{i+1}@staging.careervp.com",
            "first_name": random.choice(first_names),
            "last_name": random.choice(last_names),
            "country": random.choice(countries),
            "subscription_tier": random.choice(subscription_tiers),
            "is_active": True,
            "created_at": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        users.append(user)

    return users


def generate_test_jobs() -> list[dict[str, Any]]:
    """Generate synthetic test jobs."""
    job_titles = [
        "Software Engineer",
        "Senior Software Engineer",
        "Full Stack Developer",
        "Backend Developer",
        "Frontend Developer",
        "DevOps Engineer",
        "Data Scientist",
        "Product Manager",
        "UX Designer",
        "QA Engineer",
        "Machine Learning Engineer",
        "Security Engineer",
        "Cloud Architect",
        "Technical Lead",
        "Engineering Manager",
    ]

    companies = [
        "TechCorp",
        "InnovateTech",
        "CloudSystems",
        "DataDriven Inc",
        "SecureNet",
        "AIVentures",
        "DigitalFirst",
        "FutureSoft",
        "NextGen Labs",
        "QuantumCode",
    ]

    countries = ["ISRAEL", "USA"]
    job_types = ["FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP"]
    experience_levels = ["ENTRY", "MID", "SENIOR", "LEAD", "EXECUTIVE"]

    jobs = []
    for i in range(NUM_TEST_JOBS):
        job = {
            "job_id": str(uuid.uuid4()),
            "title": random.choice(job_titles),
            "company": random.choice(companies),
            "country": random.choice(countries),
            "job_type": random.choice(job_types),
            "experience_level": random.choice(experience_levels),
            "description": f"Looking for a talented {random.choice(job_titles)} to join our team.",
            "requirements": [
                "3+ years of experience",
                "Bachelor's degree or equivalent",
                "Strong communication skills",
            ],
            "is_active": True,
            "created_at": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        jobs.append(job)

    return jobs


def generate_test_cvs() -> list[dict[str, Any]]:
    """Generate synthetic test CVs."""
    cvs = []

    # Sample CV 1 - Software Engineer
    cvs.append({
        "cv_id": str(uuid.uuid4()),
        "user_id": "{{USER_ID_1}}",
        "file_name": "software_engineer_resume.pdf",
        "file_type": "application/pdf",
        "summary": "Experienced software engineer with 5 years of experience in full-stack development.",
        "experience": [
            {
                "title": "Software Engineer",
                "company": "TechCorp",
                "start_date": "2020-01",
                "end_date": "Present",
                "description": "Developed microservices using Python and React."
            },
            {
                "title": "Junior Developer",
                "company": "StartupXYZ",
                "start_date": "2018-06",
                "end_date": "2019-12",
                "description": "Built REST APIs and front-end components."
            }
        ],
        "skills": ["Python", "JavaScript", "React", "AWS", "Docker", "Kubernetes", "SQL", "NoSQL"],
        "education": [
            {
                "degree": "B.Sc. Computer Science",
                "institution": "Technion",
                "year": 2018
            }
        ],
        "created_at": datetime.now().isoformat(),
    })

    # Sample CV 2 - Data Scientist
    cvs.append({
        "cv_id": str(uuid.uuid4()),
        "user_id": "{{USER_ID_2}}",
        "file_name": "data_scientist_resume.pdf",
        "file_type": "application/pdf",
        "summary": "Data scientist with expertise in machine learning and statistical analysis.",
        "experience": [
            {
                "title": "Data Scientist",
                "company": "DataDriven Inc",
                "start_date": "2021-03",
                "end_date": "Present",
                "description": "Built ML models for predictive analytics."
            }
        ],
        "skills": ["Python", "R", "TensorFlow", "PyTorch", "SQL", "Tableau", "Statistics"],
        "education": [
            {
                "degree": "M.Sc. Data Science",
                "institution": "Tel Aviv University",
                "year": 2021
            }
        ],
        "created_at": datetime.now().isoformat(),
    })

    return cvs


def main() -> None:
    """Main entry point for data generation."""
    output_dir = Path(__file__).parent.parent / "payloads"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate and save test users
    users = generate_test_users()
    users_file = output_dir / "staging_test_users.json"
    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)
    print(f"Generated {len(users)} test users -> {users_file}")

    # Generate and save test jobs
    jobs = generate_test_jobs()
    jobs_file = output_dir / "staging_test_jobs.json"
    with open(jobs_file, "w") as f:
        json.dump(jobs, f, indent=2)
    print(f"Generated {len(jobs)} test jobs -> {jobs_file}")

    # Generate and save test CVs
    cvs = generate_test_cvs()
    cvs_file = output_dir / "staging_test_cvs.json"
    with open(cvs_file, "w") as f:
        json.dump(cvs, f, indent=2)
    print(f"Generated {len(cvs)} test CVs -> {cvs_file}")

    print("\nSynthetic data generation complete!")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
