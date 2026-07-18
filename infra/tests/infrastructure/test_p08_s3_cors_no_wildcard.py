"""P-08: CV/generated bucket S3 CORS must not allow a wildcard origin.

RED test cited by specs/P-08-P-10-P-11-cors-waf-spec.md, AC-P08-1.
"""

from __future__ import annotations

from aws_cdk.assertions import Template


def _cors_rules_for_bucket_containing(
    synthesized_template: Template, name_fragment: str
) -> list[dict]:
    buckets = synthesized_template.find_resources("AWS::S3::Bucket")
    matches = [
        props
        for props in buckets.values()
        if name_fragment in str(props["Properties"].get("BucketName", ""))
    ]
    assert matches, f"No bucket found with name containing {name_fragment!r}"
    rules: list[dict] = []
    for props in matches:
        cors = props["Properties"].get("CorsConfiguration", {})
        rules.extend(cors.get("CorsRules", []))
    return rules


def test_p08_s3_cors_has_no_wildcard_origin(synthesized_template: Template) -> None:
    """CV and VPR-results (generated) bucket CORS must list explicit origins only."""
    for fragment in ("cvs", "vpr-results"):
        rules = _cors_rules_for_bucket_containing(synthesized_template, fragment)
        assert rules, f"No CORS rules found for bucket containing {fragment!r}"
        for rule in rules:
            origins = rule.get("AllowedOrigins", [])
            for origin in origins:
                assert "*" not in origin, (
                    f"wildcard origin {origin!r} present in CORS rule for "
                    f"bucket containing {fragment!r}"
                )


def test_p08_s3_cors_dev_is_localhost_only(synthesized_template: Template) -> None:
    """Dev env CORS origins must be localhost only (no deployed frontend domain)."""
    for fragment in ("cvs", "vpr-results"):
        rules = _cors_rules_for_bucket_containing(synthesized_template, fragment)
        for rule in rules:
            origins = rule.get("AllowedOrigins", [])
            assert origins == ["http://localhost:3000"], (
                f"dev CORS origins for bucket containing {fragment!r} must be "
                f"localhost-only, got {origins!r}"
            )
