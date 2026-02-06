"""
This script is designed to download and save the Swagger JSON configuration from an AWS Cloud Development Kit (CDK) deployed service.
It's particularly useful for automating the process of fetching Swagger documentation for APIs created using Powertools for Lambda since their swagger endpoint support a JSON download option.
You can place the swagger file under your docs folder and publish it as part of your PR changes.
When you run the 'make pr' command, it will run automatically run this script and save its' output to the default location where it will be uploaded to GitHub pages.

The script uses AWS Boto3 to interact with AWS services, and the 'requests' library to download the Swagger JSON.

Usage:
    The script accepts command-line arguments for customization:
    --out-destination: Specifies the directory where the Swagger JSON will be saved. (Default: 'docs/swagger')
    --out-filename: Specifies the filename for the saved Swagger JSON. (Default: 'openapi.json')
    --swagger-url-key: The key for the Swagger URL in the CDK stack outputs. (Default: 'SwaggerURL')
    --stack-name: (Optional) The name of the CDK stack to use. If not provided, the 'get_stack_name' function from the cdk folder will be used

Example:
    python generate_openapi.py --out-destination './docs/swagger' --out-filename 'openapi.json' --swagger-url-key 'SwaggerURL' --stack-name 'MyStack'
"""

import argparse
import json
import os
import time
from typing import Any, Dict, Optional

import boto3
import requests
from cdk.careervp.utils import get_stack_name


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


def download_swagger_json(swagger_url: str, retries: int = 5, delay_seconds: float = 5.0) -> Dict[str, Any]:
    """
    Download Swagger JSON from the provided URL.

    Args:
        swagger_url (str): The URL from which to download the Swagger JSON.

    Returns:
        Dict[str, Any]: The downloaded Swagger JSON.
    """
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(f'{swagger_url}?format=json', timeout=30)
            response.raise_for_status()
            json_data = response.json()
            assert isinstance(json_data, dict), 'Swagger JSON should be a dict'
            return json_data
        except requests.HTTPError as exc:
            if attempt == retries:
                raise
            print(f'Retry {attempt} failed fetching Swagger JSON ({exc}). Retrying in {delay_seconds} seconds...')
            time.sleep(delay_seconds)
    # Should never reach due to raise on final attempt
    raise RuntimeError('Failed to download Swagger JSON after retries')


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
        swagger_json = download_swagger_json(swagger_url)
    except requests.HTTPError as err:
        print(f'Failed to download Swagger JSON: {err}')
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
