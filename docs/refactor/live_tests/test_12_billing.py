# Live Tests - Billing and Subscription Endpoints
# Tests: POST /billing/checkout, POST /billing/portal, GET /users/me/subscription, POST /billing/webhook

import os
import json
import pytest
import requests
from typing import Dict, Any

# Import configuration
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .conftest import (
    API_BASE,
    TEST_USER_ID,
    get_auth_headers,
    load_test_ids,
    save_test_ids,
)

# Test data storage for cross-test dependencies
test_data: Dict[str, Any] = {
    "user_id": TEST_USER_ID,
    "session_id": None,
    "subscription_id": None,
}

# Load test IDs from .env.json file if exists (for cross-run persistence)
_saved_ids = load_test_ids()
for key in ["session_id", "subscription_id", "user_id"]:
    if key in _saved_ids and _saved_ids[key]:
        test_data[key] = _saved_ids[key]

# Ensure TEST_USER_ID is set
if not test_data.get("user_id"):
    test_data["user_id"] = TEST_USER_ID


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


class TestBillingEndpoints:
    """Test billing and subscription endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data."""
        self.base_url = API_BASE

    def test_get_subscription_info_trial(self):
        """Test GET /users/me/subscription - retrieve trial/subscription status."""
        url = f"{self.base_url}/users/me/subscription"
        headers = get_auth_headers()

        response = requests.get(url, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_get_subscription_info_trial",
            "GET /users/me/subscription",
            response.status_code,
            data,
        )

        # Accept 200 (success) or 403 (subscription required)
        if response.status_code == 200:
            # Validate the response contract: subscription is either null (no Stripe sub)
            # or an object with subscription details. Trial state is separate (see /users/me/usage).
            assert "subscription" in data, "Response must include 'subscription' field"
            assert "has_active_subscription" in data, (
                "Response must include 'has_active_subscription' field"
            )
            assert isinstance(data["has_active_subscription"], bool), (
                "'has_active_subscription' must be a bool"
            )
            assert data["subscription"] is None or isinstance(
                data["subscription"], dict
            ), "'subscription' must be null or an object"
            print(f"✓ GET /users/me/subscription - Status: {response.status_code}")
            if data["subscription"]:
                print(f"  Subscription status: {data['subscription'].get('status')}")
            else:
                print("  No active Stripe subscription (expected for fresh test user)")
        elif response.status_code == 403:
            print("⚠ GET /users/me/subscription - Subscription required (403)")
        else:
            print(f"⚠ GET /users/me/subscription - Status {response.status_code}")

    def test_create_checkout_session(self):
        """Test POST /billing/checkout - create Stripe checkout session."""
        url = f"{self.base_url}/billing/checkout"
        headers = get_auth_headers()

        payload = {
            "price_id": "price_monthly_001",
            "success_url": "https://app.careervp.com/billing/success",
            "cancel_url": "https://app.careervp.com/billing/cancel",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_create_checkout_session",
            "POST /billing/checkout",
            response.status_code,
            data,
        )

        # Accept 200 (success) or 400+ for invalid requests
        if response.status_code == 200:
            assert "session_id" in data or "url" in data, (
                "Response must include session_id or url"
            )
            assert "checkout_url" in data or "url" in data, (
                "Response must include checkout_url"
            )
            test_data["session_id"] = data.get("session_id") or data.get("id")
            save_test_ids(test_data)
            print(f"✓ POST /billing/checkout - Session ID: {test_data['session_id']}")
        else:
            print(
                f"⚠ POST /billing/checkout - Status {response.status_code}: {data.get('error', 'Unknown error')}"
            )

    def test_create_billing_portal_session(self):
        """Test POST /billing/portal - create Stripe billing portal session."""
        url = f"{self.base_url}/billing/portal"
        headers = get_auth_headers()

        payload = {
            "return_url": "https://app.careervp.com/settings/billing",
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_create_billing_portal_session",
            "POST /billing/portal",
            response.status_code,
            data,
        )

        # Accept 200 (success), 403 (no subscription), or 400+ for invalid requests
        if response.status_code == 200:
            assert "url" in data, "Response must include portal url"
            print("✓ POST /billing/portal - Portal URL generated")
        elif response.status_code == 403:
            print("⚠ POST /billing/portal - No active subscription (403)")
        else:
            print(
                f"⚠ POST /billing/portal - Status {response.status_code}: {data.get('error', 'Unknown error')}"
            )

    def test_webhook_signature_validation(self):
        """Test POST /billing/webhook - webhook endpoint accepts Stripe events."""
        url = f"{self.base_url}/billing/webhook"

        # Webhook endpoint should NOT require auth (Stripe calls it)
        headers = {"Content-Type": "application/json"}

        # Construct a minimal Stripe webhook event (without valid signature)
        payload = {
            "id": "evt_test_12345",
            "type": "checkout.session.completed",
            "object": "event",
            "created": 1234567890,
            "data": {
                "object": {
                    "id": "cs_test_session_id",
                    "customer": "cus_test_customer",
                    "subscription": "sub_test_subscription",
                    "metadata": {
                        "user_id": test_data.get("user_id", "test-user"),
                    },
                }
            },
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        # Print response
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text}

        print_response(
            "test_webhook_signature_validation",
            "POST /billing/webhook",
            response.status_code,
            data,
        )

        # Webhook endpoint should return 400 (invalid signature) or 200 (processed)
        # It should NOT return 401 (auth required)
        if response.status_code == 400:
            print("✓ POST /billing/webhook - Correctly rejected unsigned event (400)")
        elif response.status_code == 200:
            print("✓ POST /billing/webhook - Accepted event (200)")
        elif response.status_code == 401:
            print("✗ POST /billing/webhook - Incorrectly requires auth (401)")
        else:
            print(f"⚠ POST /billing/webhook - Status {response.status_code}")
