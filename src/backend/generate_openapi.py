"""Generate OpenAPI JSON from deployed API Gateway route resources."""

import argparse
import json
import os
import re
from typing import Any, Dict, Optional

import boto3
from cdk.careervp.utils import get_stack_name

PATH_NORMALIZATION_OVERRIDES = {
    '/company-research/{jobId}': '/company-research/{company_name}',
}

PATH_PARAMETER_REPLACEMENTS = {
    '{jobId}': '{job_id}',
    '{vprId}': '{job_id}',
    '{cvTailoringId}': '{job_id}',
    '{coverLetterId}': '{job_id}',
    '{interviewPrepId}': '{job_id}',
}


def normalize_route_path(path: str) -> str:
    """Normalize deployed legacy path-parameter names to canonical contract names."""
    normalized = PATH_NORMALIZATION_OVERRIDES.get(path, path)
    for legacy, canonical in PATH_PARAMETER_REPLACEMENTS.items():
        normalized = normalized.replace(legacy, canonical)
    return normalized


def get_cdk_stack_outputs(stack_name: Optional[str] = None) -> Dict[str, str]:
    """
    Get outputs from a specified CDK stack.

    Args:
        stack_name (str, optional): The name of the CDK stack. If not provided, the 'get_stack_name' function from the cdk folder will be used

    Returns:
        Dict[str, str]: A dictionary of stack outputs.
    """
    client = boto3.client('cloudformation')
    stack_name_to_use = stack_name if stack_name else get_stack_name()
    response = client.describe_stacks(StackName=stack_name_to_use)
    outputs = response['Stacks'][0]['Outputs']
    return {output['OutputKey']: output['OutputValue'] for output in outputs}


def parse_api_id_from_swagger_url(swagger_url: str) -> str:
    """Extract API Gateway REST API id from execute-api URL."""
    match = re.match(r'https://([a-z0-9]+)\.execute-api\.[a-z0-9-]+\.amazonaws\.com/.+', swagger_url)
    if not match:
        raise ValueError(f'Unable to parse API id from SwaggerURL: {swagger_url}')
    return match.group(1)


def get_apigateway_resource_items(rest_api_id: str) -> list[dict[str, Any]]:
    """Fetch all API Gateway resources for the given REST API id."""
    client = boto3.client('apigateway')
    paginator = client.get_paginator('get_resources')
    items: list[dict[str, Any]] = []
    for page in paginator.paginate(restApiId=rest_api_id):
        page_items = page.get('items', [])
        if isinstance(page_items, list):
            items.extend(item for item in page_items if isinstance(item, dict))
    return items


def build_openapi_from_apigw_resources(resources: list[dict[str, Any]]) -> Dict[str, Any]:
    """Build a minimal OpenAPI document from API Gateway resources/methods."""
    excluded_paths = {'/swagger', '/swagger.css', '/swagger.js'}
    paths: dict[str, dict[str, Any]] = {}

    for resource in resources:
        path = resource.get('path')
        if not isinstance(path, str) or not path or path in excluded_paths:
            continue
        normalized_path = normalize_route_path(path)

        resource_methods = resource.get('resourceMethods')
        if not isinstance(resource_methods, dict):
            continue

        for method in sorted(resource_methods.keys()):
            method_upper = str(method).upper()
            if method_upper == 'OPTIONS':
                continue
            method_lower = method_upper.lower()
            path_item = paths.setdefault(normalized_path, {})
            path_item[method_lower] = {
                'responses': {
                    '200': {'description': 'OK'},
                }
            }

    return {
        'openapi': '3.0.1',
        'info': {'title': 'CareerVP Canonical API', 'version': 'staging-v1'},
        'paths': dict(sorted(paths.items(), key=lambda kv: kv[0])),
    }


def save_json_to_file(json_data: Dict[str, Any], file_path: str) -> None:
    """
    Save JSON data to a file.

    Args:
        json_data (Dict[str, Any]): JSON data to save.
        file_path (str): The file path where the JSON data will be saved.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(json_data, file, indent=4)


def main(out_destination: str, out_filename: str, swagger_url_key: str, stack_name: Optional[str] = None) -> None:
    """
    Main function that orchestrates the download and saving of Swagger JSON.

    Args:
        out_destination (str): The directory to save the Swagger JSON. Default is 'docs/swagger'.
        out_filename (str): The filename for the Swagger JSON. Default is 'openapi.json'.
        swagger_url_key (str): The key for the Swagger URL in CDK stack outputs. Default is 'SwaggerURL'.
        stack_name (str, optional): The name of the CDK stack to use.
    """
    outputs = get_cdk_stack_outputs(stack_name)
    swagger_url = outputs.get(swagger_url_key)
    if not swagger_url:
        msg = f'Swagger endpoint URL with key "{swagger_url_key}" not found in stack outputs.'
        print(msg)
        raise SystemExit(1)

    try:
        rest_api_id = parse_api_id_from_swagger_url(swagger_url)
        resources = get_apigateway_resource_items(rest_api_id)
        swagger_json = build_openapi_from_apigw_resources(resources)
    except Exception as err:  # noqa: BLE001
        print(f'Failed to generate OpenAPI from API Gateway resources: {err}')
        raise SystemExit(1) from err

    file_path = os.path.join(out_destination, out_filename)
    save_json_to_file(swagger_json, file_path)
    print(f'Swagger JSON saved to {file_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and save Swagger JSON')
    parser.add_argument(
        '--out-destination', type=str, default='docs/swagger', help='Output destination directory for Swagger JSON (default: docs/swagger)'
    )
    parser.add_argument('--out-filename', type=str, default='openapi.json', help='Output filename for Swagger JSON (default: openapi.json)')
    parser.add_argument('--swagger-url-key', type=str, default='SwaggerURL', help='Key for Swagger URL in CDK stack outputs (default: SwaggerURL)')
    parser.add_argument(
        '--stack-name',
        type=str,
        help='Name of the CDK stack to use (optional), If not provided, the get_stack_name function from the CDK folder will be used',
    )

    args = parser.parse_args()

    main(args.out_destination, args.out_filename, args.swagger_url_key, args.stack_name)
