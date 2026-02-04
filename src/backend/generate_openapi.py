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
    --mode: Operation mode - 'download' (default, from AWS) or 'local' (use existing file, no AWS needed)

Example:
    python generate_openapi.py --out-destination './docs/swagger' --out-filename 'openapi.json' --swagger-url-key 'SwaggerURL' --stack-name 'MyStack'

Local Mode (no AWS credentials needed):
    python generate_openapi.py --mode local --out-destination './docs/swagger' --out-filename 'openapi.json'
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional, cast

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


def download_swagger_json(swagger_url: str) -> Dict[str, Any]:
    """
    Download Swagger JSON from the provided URL.

    Args:
        swagger_url (str): The URL from which to download the Swagger JSON.

    Returns:
        Dict[str, Any]: The downloaded Swagger JSON.
    """
    response = requests.get(f'{swagger_url}?format=json')
    response.raise_for_status()
    return cast(Dict[str, Any], response.json())


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


def load_local_openapi(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load existing OpenAPI file from disk.

    Args:
        file_path (str): Path to the OpenAPI JSON file.

    Returns:
        Optional[Dict[str, Any]]: The loaded OpenAPI data, or None if file doesn't exist.
    """
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r') as file:
        return cast(Dict[str, Any], json.load(file))


def download_and_save_swagger(out_destination: str, out_filename: str, swagger_url_key: str, stack_name: Optional[str] = None) -> bool:
    """
    Download Swagger from AWS and save to file.

    Args:
        out_destination: Directory to save the Swagger JSON.
        out_filename: Filename for the Swagger JSON.
        swagger_url_key: Key for Swagger URL in CDK stack outputs.
        stack_name: Optional CDK stack name.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        outputs = get_cdk_stack_outputs(stack_name)
        swagger_url = outputs.get(swagger_url_key)
        if swagger_url:
            swagger_json = download_swagger_json(swagger_url)
            file_path = os.path.join(out_destination, out_filename)
            save_json_to_file(swagger_json, file_path)
            print(f'Swagger JSON saved to {file_path}')
            return True
        else:
            print(f'Swagger endpoint URL with key "{swagger_url_key}" not found in stack outputs.')
            return False
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print('WARNING: /swagger endpoint not found on deployed API.')
            print('This usually means the Lambda handler does not expose a swagger endpoint.')
            print('The local docs/swagger/openapi.json file is still valid.')
            return True  # Exit gracefully, not a failure
        print(f'Error downloading Swagger JSON: {e}')
        return False
    except Exception as e:
        print(f'Error downloading Swagger JSON: {e}')
        return False


def local_mode_copy(out_destination: str, out_filename: str) -> bool:
    """
    Local mode: Copy existing OpenAPI file to destination without AWS.

    This mode is used for CI/CD validation without AWS credentials.
    It ensures the OpenAPI file exists and is valid JSON.

    Args:
        out_destination: Directory to save the Swagger JSON.
        out_filename: Filename for the Swagger JSON.

    Returns:
        bool: True if successful, False otherwise.
    """
    # Look for existing OpenAPI file in standard locations
    search_paths = [
        'docs/swagger/openapi.json',
        'docs/openapi.json',
        'openapi.json',
        'src/backend/docs/swagger/openapi.json',
    ]

    existing_file = None
    for path in search_paths:
        if os.path.exists(path):
            existing_file = path
            break

    if not existing_file:
        print('Error: No existing OpenAPI file found. Searched:')
        for path in search_paths:
            print(f'  - {path}')
        return False

    # Copy to destination
    output_path = os.path.join(out_destination, out_filename)
    try:
        data = load_local_openapi(existing_file)
        if data is None:
            print(f'Error: Could not read existing OpenAPI file: {existing_file}')
            return False

        # Validate it's valid JSON and save
        json.dumps(data, indent=4)  # Validate JSON is serializable
        save_json_to_file(data, output_path)
        print(f'Local OpenAPI copied to {output_path}')
        return True
    except Exception as e:
        print(f'Error copying local OpenAPI: {e}')
        return False


def main(out_destination: str, out_filename: str, swagger_url_key: str, stack_name: Optional[str] = None, mode: str = 'download') -> int:
    """
    Main function that orchestrates the download and saving of Swagger JSON.

    Args:
        out_destination (str): The directory to save the Swagger JSON. Default is 'docs/swagger'.
        out_filename (str): The filename for the Swagger JSON. Default is 'openapi.json'.
        swagger_url_key (str): The key for the Swagger URL in CDK stack outputs. Default is 'SwaggerURL'.
        stack_name (str, optional): The name of the CDK stack to use.
        mode (str): 'download' (from AWS) or 'local' (use existing file).

    Returns:
        int: 0 for success, 1 for failure.
    """
    if mode == 'local':
        success = local_mode_copy(out_destination, out_filename)
        return 0 if success else 1

    # Default: download from AWS
    success = download_and_save_swagger(out_destination, out_filename, swagger_url_key, stack_name)
    return 0 if success else 1


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
    parser.add_argument(
        '--mode',
        type=str,
        default='download',
        choices=['download', 'local'],
        help='Operation mode: download (from AWS) or local (use existing file, no AWS needed). Default: download',
    )

    args = parser.parse_args()

    exit_code = main(args.out_destination, args.out_filename, args.swagger_url_key, args.stack_name, args.mode)
    sys.exit(exit_code)
