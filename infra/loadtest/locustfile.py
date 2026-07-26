"""P-20 minimal load harness: hub read + one generate flow.

Run in smoke mode, e.g.:

    LOAD_TEST_AUTH_TOKEN=<bearer token> \\
    LOAD_TEST_APPLICATION_ID=<application_id> \\
    uv run --project infra --extra loadtest locust -f infra/loadtest/locustfile.py \\
        --host https://<api-id>.execute-api.us-east-1.amazonaws.com/prod \\
        --headless --users 3 --spawn-rate 3 --run-time 20s --csv /tmp/p20-smoke

Thresholds (`infra/loadtest/load_harness_config.json`) are evaluated by hand against the
generated `/tmp/p20-smoke_stats.csv` after the run; this file only generates the traffic.
The generate-flow user's `wait_time` is intentionally long so a short smoke run produces
at most one `/vpr/generate` call, since that endpoint triggers a real paid model invocation.
"""

from __future__ import annotations

import os

from locust import HttpUser, between, task

AUTH_TOKEN = os.environ.get("LOAD_TEST_AUTH_TOKEN", "")
APPLICATION_ID = os.environ.get("LOAD_TEST_APPLICATION_ID", "smoke-test-application")
CV_ID = os.environ.get("LOAD_TEST_CV_ID", "smoke-test-cv")
JOB_ID = os.environ.get("LOAD_TEST_JOB_ID", "smoke-test-job")


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else {}


class HubReadUser(HttpUser):
    """Repeated hub reads — the steady-state traffic pattern the throttle must survive."""

    weight = 5
    wait_time = between(1, 2)

    @task
    def hub_read(self) -> None:
        self.client.get(
            f"/applications/{APPLICATION_ID}",
            headers=_auth_headers(),
            name="/applications/[id] (hub read)",
        )


class GenerateFlowUser(HttpUser):
    """One generate-flow call per smoke run — real cost, so kept to a single iteration."""

    weight = 1
    wait_time = between(9999, 10000)

    @task
    def generate_vpr(self) -> None:
        self.client.post(
            "/vpr/generate",
            json={"cv_id": CV_ID, "job_id": JOB_ID, "gap_response_ids": []},
            headers=_auth_headers(),
            name="/vpr/generate (one generate flow)",
        )
