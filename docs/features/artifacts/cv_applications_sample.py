"""
Sample CV Applications for E2E Testing (9 applications for 10 total runs)

Each application contains:
- position: Job title/role
- company: Company name
- job_description: Full JD text
- preferences: Optional tailoring preferences

To use: Run this with the E2E test to execute 9 CV tailoring operations.
"""

import json
import uuid
from typing import Any


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


# 9 Different Job Applications for comprehensive testing
CV_APPLICATIONS = [
    {
        "id": "app-001",
        "position": "Senior Python Developer - Cloud Infrastructure",
        "company": "CloudScale Tech",
        "job_description": """
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
""",
        "preferences": {
            "tone": "professional",
            "target_length": "one_page",
            "emphasis_areas": ["python", "aws", "cloud_infrastructure"]
        }
    },
    {
        "id": "app-002",
        "position": "Backend Engineer - FinTech",
        "company": "PayFlow Financial",
        "job_description": """
Backend Engineer - FinTech

PayFlow is revolutionizing digital payments. We're looking for a Backend Engineer
to build secure, scalable payment processing systems.

Key Responsibilities:
- Design and develop payment processing APIs
- Implement fraud detection algorithms
- Ensure PCI-DSS compliance in all implementations
- Build real-time transaction processing systems
- Integrate with banking APIs and payment gateways
- Write comprehensive unit and integration tests

Required Skills:
- 4+ years of backend development experience
- Strong Python or Java programming skills
- Experience with SQL databases (PostgreSQL, MySQL)
- Understanding of financial transaction flows
- Knowledge of security best practices
- Experience with message queues (RabbitMQ, Kafka)

Preferred Qualifications:
- Experience with payment gateways (Stripe, PayPal)
- Knowledge of blockchain/cryptocurrency
- Experience with real-time streaming (Apache Kafka)
- Background in financial services or fintech

What We Offer:
- Competitive salary ($120K-$180K)
- Equity package
- Hybrid work model
- Learning and development budget
- Health benefits
""",
        "preferences": {
            "tone": "professional",
            "target_length": "one_page",
            "emphasis_areas": ["python", "payment_processing", "security"]
        }
    },
    {
        "id": "app-003",
        "position": "Full Stack Developer - SaaS Startup",
        "company": "DataViz.io",
        "job_description": """
Full Stack Developer - SaaS Startup

Join our fast-growing SaaS startup building data visualization tools for enterprise customers.

Key Responsibilities:
- Develop new features for our web-based data visualization platform
- Build RESTful APIs and microservices
- Implement responsive frontend components
- Participate in code reviews and pair programming
- Contribute to architectural decisions
- Write clean, maintainable code

Required Skills:
- 3+ years of full-stack development experience
- Strong Python backend skills (Django or FastAPI)
- React or Vue.js frontend experience
- PostgreSQL or MongoDB database experience
- Git version control
- Understanding of SaaS architecture patterns

Preferred Qualifications:
- Experience with data visualization libraries (D3.js, Plotly)
- TypeScript experience
- AWS or GCP cloud experience
- Startup experience
- Experience with GraphQL

What We Offer:
- Early-stage equity opportunity
- Flexible working hours
- Modern office in tech hub
- Team events and activities
- Competitive salary
""",
        "preferences": {
            "tone": "innovative",
            "target_length": "one_page",
            "emphasis_areas": ["python", "react", "full_stack"]
        }
    },
    {
        "id": "app-004",
        "position": "DevOps Engineer - Platform Team",
        "company": "StreamCloud Systems",
        "job_description": """
DevOps Engineer - Platform Team

Build and maintain our cloud platform infrastructure supporting millions of users.

Key Responsibilities:
- Design and maintain CI/CD pipelines
- Manage Kubernetes clusters at scale
- Implement monitoring and alerting systems
- Automate infrastructure provisioning with Terraform
- Ensure high availability and disaster recovery
- Optimize cloud costs

Required Skills:
- 4+ years of DevOps/SRE experience
- Strong AWS expertise (EC2, RDS, S3, Lambda, EKS)
- Kubernetes production experience
- Terraform or similar IaC tools
- Experience with CI/CD tools (Jenkins, GitHub Actions, GitLab CI)
- Scripting skills (Python, Bash)

Preferred Qualifications:
- Experience with service mesh (Istio, Linkerd)
- Knowledge of observability tools (Prometheus, Grafana, Datadog)
- Experience with multi-region deployments
- Security certifications
- Experience with database administration

What We Offer:
- Competitive salary ($140K-$200K)
- Top-tier equipment
- Remote-friendly
- Annual bonuses
- Professional development
""",
        "preferences": {
            "tone": "technical",
            "target_length": "one_page",
            "emphasis_areas": ["aws", "kubernetes", "devops"]
        }
    },
    {
        "id": "app-005",
        "position": "Machine Learning Engineer",
        "company": "AI Dynamics Lab",
        "job_description": """
Machine Learning Engineer

Join our research team building cutting-edge ML models for enterprise applications.

Key Responsibilities:
- Design and implement machine learning models
- Build ML pipelines for training and deployment
- Optimize models for production performance
- Collaborate with data scientists and engineers
- Evaluate model performance and accuracy
- Contribute to MLOps best practices

Required Skills:
- 3+ years of ML engineering experience
- Strong Python skills (NumPy, Pandas, Scikit-learn)
- Deep learning frameworks (PyTorch, TensorFlow)
- Experience with ML model deployment (SageMaker, MLflow)
- Understanding of ML Ops practices
- Statistical analysis and experimentation

Preferred Qualifications:
- Experience with LLMs and NLP
- Computer vision experience
- AWS certification
- Research publications
- Experience with distributed training

What We Offer:
- Research-focused environment
- Conference budget
- High-end hardware
- Competitive salary
- Equity opportunities
""",
        "preferences": {
            "tone": "research_focused",
            "target_length": "one_page",
            "emphasis_areas": ["python", "machine_learning", "aws"]
        }
    },
    {
        "id": "app-006",
        "position": "Engineering Manager - Platform",
        "company": "ScaleUp Technologies",
        "job_description": """
Engineering Manager - Platform

Lead our platform engineering team building tools for developer productivity.

Key Responsibilities:
- Manage and grow a team of 6-8 engineers
- Drive technical strategy and architecture decisions
- Improve developer experience and productivity
- Collaborate with product and design teams
- Establish engineering best practices
- Mentor engineers in their career growth

Required Skills:
- 5+ years of software engineering experience
- 2+ years of engineering management experience
- Strong technical background (Python, AWS)
- Experience with agile methodologies
- Excellent communication skills
- Experience with cloud platforms

Preferred Qualifications:
- Experience building developer tools
- Background in platform engineering
- Experience with microservices
- Startup growth experience
- Technical blog or open source contributions

What We Offer:
- Senior leadership role
- Competitive salary ($180K-$250K)
- Equity package
- Generous PTO
- Health and wellness benefits
""",
        "preferences": {
            "tone": "leadership",
            "target_length": "one_page",
            "emphasis_areas": ["engineering_management", "python", "aws"]
        }
    },
    {
        "id": "app-007",
        "position": "Security Engineer",
        "company": "SecureNet Corp",
        "job_description": """
Security Engineer

Help us build secure systems protecting sensitive customer data.

Key Responsibilities:
- Implement security controls and best practices
- Conduct security reviews and assessments
- Respond to security incidents
- Build security automation tools
- Collaborate with development teams
- Ensure compliance with security standards

Required Skills:
- 4+ years of security engineering experience
- Strong Python scripting skills
- Experience with cloud security (AWS, Azure, GCP)
- Knowledge of security frameworks (SOC2, ISO 27001)
- Experience with penetration testing
- Understanding of cryptography

Preferred Qualifications:
- Security certifications (CISSP, CEH, OSCP)
- Experience with DevSecOps
- Cloud security certifications
- Incident response experience
- Security tool development

What We Offer:
- Critical role in security
- Competitive salary
- Certifications support
- Remote options
- Comprehensive benefits
""",
        "preferences": {
            "tone": "security_focused",
            "target_length": "one_page",
            "emphasis_areas": ["security", "python", "aws"]
        }
    },
    {
        "id": "app-008",
        "position": "Data Engineer - Analytics Platform",
        "company": "InsightHub Analytics",
        "job_description": """
Data Engineer - Analytics Platform

Build the data infrastructure powering our business intelligence and analytics platform.

Key Responsibilities:
- Design and build data pipelines
- Implement data warehouse solutions
- Build real-time and batch processing systems
- Ensure data quality and reliability
- Optimize query performance
- Collaborate with data analysts and scientists

Required Skills:
- 4+ years of data engineering experience
- Strong Python and SQL skills
- Experience with data warehouses (Snowflake, Redshift, BigQuery)
- ETL/ELT pipeline development
- Experience with Apache Spark or similar
- Cloud data services experience

Preferred Qualifications:
- Experience with streaming data (Kafka, Kinesis)
- Data modeling expertise
- dbt experience
- AWS data certifications
- Experience with BI tools

What We Offer:
- Data-intensive work
- Competitive salary
- Modern data stack
- Team collaboration
- Growth opportunities
""",
        "preferences": {
            "tone": "analytical",
            "target_length": "one_page",
            "emphasis_areas": ["python", "data_engineering", "aws"]
        }
    },
    {
        "id": "app-009",
        "position": "Site Reliability Engineer",
        "company": "HighLoad Systems",
        "job_description": """
Site Reliability Engineer (SRE)

Ensure our systems remain reliable, available, and performant under heavy load.

Key Responsibilities:
- Monitor and improve system reliability
- Respond to production incidents
- Build monitoring and alerting systems
- Conduct capacity planning
- Automate operational tasks
- Document runbooks and procedures

Required Skills:
- 4+ years of SRE/DevOps experience
- Strong Linux administration skills
- Experience with AWS services
- Scripting skills (Python, Bash)
- Monitoring and observability tools
- Incident response experience

Preferred Qualifications:
- Experience with chaos engineering
- SRE certifications
- Performance optimization experience
- Multi-region deployment experience
- Custom tooling development

What We Offer:
- On-call compensation
- Competitive salary
- Modern tech stack
- Professional development
- Work-life balance
""",
        "preferences": {
            "tone": "reliability_focused",
            "target_length": "one_page",
            "emphasis_areas": ["aws", "kubernetes", "monitoring"]
        }
    },
]


def get_applications() -> list[dict[str, Any]]:
    """Return the list of CV applications for testing."""
    return CV_APPLICATIONS


def get_application_by_id(app_id: str) -> dict[str, Any] | None:
    """Get a specific application by ID."""
    for app in CV_APPLICATIONS:
        if app["id"] == app_id:
            return app
    return None


def get_test_config() -> dict[str, Any]:
    """Generate test configuration for E2E test."""
    return {
        "applications": CV_APPLICATIONS,
        "cv_text": SAMPLE_CV_TEXT,
        "user_id": "e2e-test-user-" + str(uuid.uuid4())[:8],
        "description": "E2E Test Configuration for 9 CV Applications"
    }


if __name__ == "__main__":
    # Output the config as JSON for external use
    config = get_test_config()
    print(json.dumps(config, indent=2))
