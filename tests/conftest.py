"""
Pytest configuration and fixtures for CETI data-ingest tests.

This module provides fixtures that work with both LocalStack (local testing)
and real AWS (CI/CD with credentials).
"""

import os
import boto3
import pytest
from botocore.exceptions import ClientError


@pytest.fixture(scope="session")
def aws_endpoint_url():
    """
    Return AWS endpoint URL for S3.

    - Returns LocalStack URL if AWS_ENDPOINT_URL is set (local testing)
    - Returns None for real AWS (production/CI with credentials)
    """
    return os.getenv("AWS_ENDPOINT_URL")


@pytest.fixture(scope="session")
def aws_credentials():
    """
    Return AWS credentials from environment.

    Falls back to 'cetitest' credentials for LocalStack if not set.
    """
    return {
        'aws_access_key_id': os.getenv("AWS_ACCESS_KEY_ID", "cetitest"),
        'aws_secret_access_key': os.getenv("AWS_SECRET_ACCESS_KEY", "cetitest"),
        'region_name': os.getenv("AWS_REGION", "us-east-1")
    }


@pytest.fixture(scope="session")
def s3_client(aws_endpoint_url, aws_credentials):
    """
    Create S3 client for testing.

    Automatically points to:
    - LocalStack if AWS_ENDPOINT_URL is set
    - Real AWS otherwise

    Scope: session (reused across all tests for performance)
    """
    client_kwargs = aws_credentials.copy()

    # Only set endpoint_url if it's defined (LocalStack)
    if aws_endpoint_url:
        client_kwargs['endpoint_url'] = aws_endpoint_url

    return boto3.client('s3', **client_kwargs)


@pytest.fixture(scope="session")
def test_bucket_name():
    """Return the test bucket name from environment or default."""
    return os.getenv("CETI_BUCKET", "ceti-data-test")


@pytest.fixture(scope="session")
def test_bucket(s3_client, test_bucket_name):
    """
    Create test bucket in S3 (LocalStack or real AWS).

    The bucket is created once per test session and reused.
    Scope: session

    Yields:
        str: The bucket name
    """
    try:
        # Try to create bucket
        s3_client.create_bucket(Bucket=test_bucket_name)
        print(f"\nCreated test bucket: {test_bucket_name}")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ['BucketAlreadyOwnedByYou', 'BucketAlreadyExists']:
            print(f"\nTest bucket already exists: {test_bucket_name}")
        else:
            raise

    yield test_bucket_name

    # Optional: Cleanup after all tests
    # Uncomment to delete bucket and all objects after test session
    # try:
    #     # Delete all objects first
    #     response = s3_client.list_objects_v2(Bucket=test_bucket_name)
    #     if 'Contents' in response:
    #         objects = [{'Key': obj['Key']} for obj in response['Contents']]
    #         s3_client.delete_objects(Bucket=test_bucket_name, Delete={'Objects': objects})
    #     # Delete bucket
    #     s3_client.delete_bucket(Bucket=test_bucket_name)
    #     print(f"\nCleaned up test bucket: {test_bucket_name}")
    # except Exception as e:
    #     print(f"\nWarning: Could not clean up bucket: {e}")
