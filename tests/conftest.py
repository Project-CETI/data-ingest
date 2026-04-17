import unittest.mock as mock

import boto3
import pytest
from moto import mock_aws

from ceti import s3upload

MOCK_BUCKET = "ceti-data-test"


@pytest.fixture
def s3_mock():
    """Provide a mocked S3 client with the test bucket pre-created."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=MOCK_BUCKET)
        with mock.patch.object(s3upload, "BUCKET_NAME", MOCK_BUCKET):
            yield client
