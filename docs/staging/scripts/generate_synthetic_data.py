#!/usr/bin/env python3
"""
Synthetic Data Generator for Staging Environment

Generates realistic test data for the CareerVP staging environment including:
- Test users (job seekers with various profiles)
- Test jobs (various positions and companies)
- Test CVs (sample resumes in different formats)

Usage:
    python3 docs/staging/scripts/generate_synthetic_data.py

Output:
    - docs/staging/payloads/staging_test_users.json
    - docs/staging/payloads/staging_test_jobs.json
    - docs/staging/payloads/staging_test_cvs.json
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

# Constants
NUM_TEST_USERS = 10
NUM_TEST_JOBS = 20
NUM_TEST_CVS = 5


def generate_test_users() -> list[dict[str, Any]]:
    """Generate synthetic test users."""
    first_names = [
        "John",
        "Jane",
        "Michael",
        "Sarah",
        "David",
        "Emily",
        "Robert",
        "Lisa",
        "William",
        "Jennifer",
        "James",
        "Maria",
        "Thomas",
        "Patricia",
        "Daniel",
    ]
    last_names = [
        "Smith",
        "Johnson",
        "Williams",
        "Brown",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Rodriguez",
        "Martinez",
        "Wilson",
        "Anderson",
        "Taylor",
        "Thomas",
        "Moore",
    ]
    countries = ["ISRAEL", "USA"]
    subscription_tiers = ["free", "premium", "trial"]

    users = []
    for i in range(NUM_TEST_USERS):
        # Random creation date within last 90 days
        days_ago = random.randint(1, 90)
        created_at = datetime.now() - timedelta(days=days_ago)

        user = {
            "user_id": str(uuid.uuid4()),
            "email": f"test.user{i + 1}@staging.careervp.com",
            "first_name": random.choice(first_names),
            "last_name": random.choice(last_names),
            "country": random.choice(countries),
            "subscription_tier": random.choices(
                subscription_tiers,
                weights=[50, 20, 30],  # 50% free, 20% premium, 30% trial
            )[0],
            "is_active": True,
            "created_at": created_at.isoformat(),
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
        "Junior Software Engineer",
        "Data Analyst",
        "Site Reliability Engineer",
        "Mobile Developer",
        "Business Analyst",
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

    # Weighted distribution for experience levels
    exp_weights = [
        20,
        40,
        30,
        8,
        2,
    ]  # 20% entry, 40% mid, 30% senior, 8% lead, 2% executive
    job_type_weights = [
        70,
        5,
        15,
        10,
    ]  # 70% full-time, 5% part-time, 15% contract, 10% internship

    jobs = []
    for i in range(NUM_TEST_JOBS):
        # Random creation date within last 30 days
        days_ago = random.randint(1, 30)
        created_at = datetime.now() - timedelta(days=days_ago)

        job = {
            "job_id": str(uuid.uuid4()),
            "title": random.choice(job_titles),
            "company": random.choice(companies),
            "country": random.choice(countries),
            "job_type": random.choices(job_types, weights=job_type_weights)[0],
            "experience_level": random.choices(experience_levels, weights=exp_weights)[
                0
            ],
            "description": f"Looking for a talented {random.choice(job_titles)} to join our team.",
            "requirements": [
                "3+ years of experience",
                "Bachelor's degree or equivalent",
                "Strong communication skills",
            ],
            "is_active": True,
            "created_at": created_at.isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        jobs.append(job)

    return jobs


def generate_test_cvs() -> list[dict[str, Any]]:
    """Generate synthetic test CVs."""
    # Sample data for generating diverse CVs
    profiles = [
        {
            "title": "Software Engineer",
            "skills": [
                "Python",
                "JavaScript",
                "React",
                "AWS",
                "Docker",
                "Kubernetes",
                "SQL",
                "NoSQL",
            ],
            "summary": "Experienced software engineer with 5 years of experience in full-stack development.",
        },
        {
            "title": "Data Scientist",
            "skills": [
                "Python",
                "R",
                "TensorFlow",
                "PyTorch",
                "SQL",
                "Tableau",
                "Statistics",
                "Machine Learning",
            ],
            "summary": "Data scientist with expertise in machine learning and statistical analysis.",
        },
        {
            "title": "Product Manager",
            "skills": [
                "Product Strategy",
                "Agile",
                "Jira",
                "User Research",
                "Roadmapping",
                "Analytics",
            ],
            "summary": "Product manager with experience in leading cross-functional teams.",
        },
        {
            "title": "DevOps Engineer",
            "skills": [
                "AWS",
                "Kubernetes",
                "Terraform",
                "CI/CD",
                "Linux",
                "Python",
                "Ansible",
                "Prometheus",
            ],
            "summary": "DevOps engineer specializing in cloud infrastructure and automation.",
        },
        {
            "title": "UX Designer",
            "skills": [
                "Figma",
                "Sketch",
                "User Research",
                "Prototyping",
                "Wireframing",
                "Adobe XD",
                "CSS",
            ],
            "summary": "UX designer with a passion for creating intuitive user experiences.",
        },
    ]

    cvs = []
    for i, profile in enumerate(profiles):
        # Generate user ID for the CV owner
        user_id = str(uuid.uuid4())

        cv = {
            "cv_id": str(uuid.uuid4()),
            "user_id": user_id,
            "file_name": f"{str(profile['title']).lower().replace(' ', '_')}_resume.pdf",
            "file_type": "application/pdf",
            "summary": profile["summary"],
            "experience": [
                {
                    "title": str(profile["title"]),
                    "company": f"Company{(i % 5) + 1}",
                    "start_date": f"202{4 - (i % 3)}-{random.randint(1, 12):02d}",
                    "end_date": "Present",
                    "description": f"Worked as a {profile['title']} developing innovative solutions.",
                },
                {
                    "title": "Junior " + str(profile["title"]),
                    "company": f"StartupCompany{(i % 3) + 1}",
                    "start_date": f"202{6 - (i % 3)}-{random.randint(1, 12):02d}",
                    "end_date": f"202{4 - (i % 3)}-{random.randint(1, 12):02d}",
                    "description": "Gained foundational experience in software development.",
                },
            ],
            "skills": profile["skills"],
            "education": [
                {
                    "degree": "B.Sc. Computer Science"
                    if i % 2 == 0
                    else "M.Sc. Computer Science",
                    "institution": random.choice(
                        ["Technion", "Tel Aviv University", "Hebrew University"]
                    ),
                    "year": 2018 + (i * 2),
                }
            ],
            "created_at": datetime.now().isoformat(),
        }
        cvs.append(cv)

    return cvs


def main() -> None:
    """Main entry point for data generation."""
    # Determine output directory relative to this script
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "payloads"
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
