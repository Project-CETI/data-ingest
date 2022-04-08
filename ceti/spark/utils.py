import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Sequence, Tuple
from urllib.parse import urlparse

import boto3

import ceti

# Environment
S3_BUCKET = os.getenv("S3_EMR_BUCKET") or 'ceti-dev'
BUILD_VERSION = os.getenv("BUILD_VERSION") or ceti.__version__
BUILD_RUN_ID = os.getenv("BUILD_RUN_ID") or 'MANUAL-BUILD'


def get_s3_emr_dir(job_name: str) -> Path:
    """S3 directory where the EMR job script will be stored"""
    return Path(S3_BUCKET) / 'emr' / job_name / f'{BUILD_VERSION}-{BUILD_RUN_ID}'


def upload_files(path_specs: Sequence[Tuple[str, str]]) -> None:
    """Upload files to S3 given src / dst tuples"""
    s3 = boto3.client('s3')

    for src, dst in path_specs:
        uri = urlparse(dst)
        s3.upload_file(src, uri.hostname, uri.path[1:])


def generate_bootstrap_script() -> str:
    """Create a bootstrap script for EMR cluster"""

    script = """#!/bin/sh

# Install dependencies
/usr/bin/python3 -m pip install pip --upgrade --no-warn-script-location
PATH=$PATH:/home/hadoop/.local/bin aws codeartifact login --tool pip --repository ceti --domain ceti-repo
/home/hadoop/.local/bin/pip3 install --no-warn-script-location ceti
sudo ln -s /home/hadoop/.local/bin/ceti /usr/bin/ceti
eval $(aws sts assume-role --role-arn arn:aws:iam::656606567507:role/UpdateS3Role --role-session-name testsessionname | jq -r '.Credentials | "export AWS_ACCESS_KEY_ID=\(.AccessKeyId)\nexport AWS_SECRET_ACCESS_KEY=\(.SecretAccessKey)\nexport AWS_SESSION_TOKEN=\(.SessionToken)\n"')
aws s3 cp s3://ceti-dev/MyAWSCredentialsProviderWithUri.jar /usr/share/aws/emr/emrfs/auxlib/
""".encode()

    with NamedTemporaryFile(delete=False) as f:
        f.write(script)
        return f.name
