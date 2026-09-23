"""P-10: API Gateway CORS success responses must use the env allow-list, not ALL_ORIGINS.

RED tests cited by specs/P-08-P-10-P-11-cors-waf-spec.md, AC-P10-1/AC-P10-2.

The GatewayResponse wildcard ('*' on 401/403/4xx/5xx) is a deliberate, codified
exception: contract §10's 401 -> refresh -> sign-out flow needs the browser to
see the 401 body, and error responses never carry credentials, so a wildcard
there does not expose an allow-list bypass. Only the *success*-path CORS
(the default preflight/method integration) is tightened here.
"""

from __future__ import annotations

from aws_cdk.assertions import Template

WILDCARD = "'*'"

GATEWAY_RESPONSE_TYPES = ("Default4xx", "Default5xx", "Unauthorized", "AccessDenied")


def _options_integrations(synthesized_template: Template) -> list[dict]:
    methods = synthesized_template.find_resources("AWS::ApiGateway::Method")
    return [
        props["Properties"]["Integration"]
        for props in methods.values()
        if props["Properties"].get("HttpMethod") == "OPTIONS"
        and "Integration" in props["Properties"]
    ]


def test_p10_api_cors_success_allowlist_only(synthesized_template: Template) -> None:
    """Default CORS preflight must not statically allow every origin.

    ``Cors.ALL_ORIGINS`` renders as a single static ``'*'`` response header with
    no per-request origin matching. An explicit allow-list renders as a
    ``Vary: Origin`` header plus a response template that only echoes back a
    listed origin — i.e. it can never resolve to a bare wildcard.
    """
    integrations = _options_integrations(synthesized_template)
    assert integrations, "no OPTIONS (CORS preflight) integration found"
    for integration in integrations:
        for response in integration.get("IntegrationResponses", []):
            params = response.get("ResponseParameters", {})
            acao = params.get("method.response.header.Access-Control-Allow-Origin")
            assert acao != WILDCARD, (
                "API Gateway default CORS preflight still statically allows "
                "'*' (ALL_ORIGINS) instead of the env allow-list"
            )
            assert params.get("method.response.header.Vary") == "'Origin'", (
                "explicit allow-list CORS must vary the response by request "
                "Origin (dynamic per-origin echo), not return a single static value"
            )


def test_p10_gateway_401_cors_exception_is_documented(
    synthesized_template: Template,
) -> None:
    """GatewayResponse (401/403/4xx/5xx) keeps the wildcard as a codified exception.

    This is the one place a wildcard is allowed to remain: tightening it makes
    every 401 CORS-opaque to the browser and breaks the §10 refresh-once-then
    -sign-out flow, since the browser never even gets to read the 401 body.
    """
    gateway_responses = synthesized_template.find_resources(
        "AWS::ApiGateway::GatewayResponse"
    )
    assert gateway_responses, "no GatewayResponse resources found"

    seen_types: set[str] = set()
    for props in gateway_responses.values():
        response_type = props["Properties"].get("ResponseType")
        headers = props["Properties"].get("ResponseParameters", {})
        acao = headers.get("gatewayresponse.header.Access-Control-Allow-Origin")
        assert acao == WILDCARD, (
            f"GatewayResponse {response_type} must keep the documented wildcard "
            "CORS exception so a browser-visible 401 can be read for the "
            "refresh-once-then-sign-out flow"
        )
        seen_types.add(response_type)

    for expected in ("DEFAULT_4XX", "DEFAULT_5XX", "UNAUTHORIZED", "ACCESS_DENIED"):
        assert expected in seen_types, f"missing GatewayResponse for {expected}"

    # The wildcard must not leak into any *success*-path response header —
    # confirms it really is confined to GatewayResponse, per AC-P10-1.
    integrations = _options_integrations(synthesized_template)
    for integration in integrations:
        for response in integration.get("IntegrationResponses", []):
            params = response.get("ResponseParameters", {})
            acao = params.get("method.response.header.Access-Control-Allow-Origin")
            assert acao != WILDCARD, (
                "wildcard leaked into a success-path CORS response; it must be "
                "confined to GatewayResponse only"
            )
