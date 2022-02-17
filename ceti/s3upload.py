from argparse import Namespace
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Sequence

import boto3
import botocore

from ceti.utils import sha256sum, create_hashing_progress_bar, create_uploader_progress_bar


BUCKET_NAME = os.getenv("CETI_BUCKET") or 'ceti-data'
MAX_CONCURRENCY = 20
INGESTION_DATE_UTC = datetime.now(timezone.utc).strftime('%Y-%m-%d')


def is_file_exists(s3client, bucket_name: str, s3_key: str) -> bool:
    """Check if the file with the same S3 key already exist in the cloud"""
    results = s3client.list_objects(Bucket=bucket_name, Prefix=s3_key)

    if ('Contents' in results):
        return True

    return False


def get_filelist(src_dir: str) -> Sequence[Path]:
    """Create a list of files to be uploaded from the data directory"""

    path = Path(src_dir)
    return [p for p in sorted(path.glob('**/*')) if p.is_file()]


def to_s3_key(data_dir: str, src: Path) -> Path:
    """Create S3 key to address the file in the bucket"""

    filename = src.relative_to(data_dir)

    with create_hashing_progress_bar(src) as progress:
        hash = sha256sum(str(src.resolve()), callback=progress.update)

    if not re.match(r".+\/.+", str(filename)):
        # The file we are trying to upload is not
        # in the local folder that defines the device
        # that captured this file.
        # Therefore, it should be uploaded into
        # the "/unknown-device/" folder in S3
        filename = Path("unknown-device")

    return Path('raw') / INGESTION_DATE_UTC / filename.parent / hash / filename.name


def sync_files(s3client, data_dir: str, filelist: Sequence[Path]) -> None:
    """Execute file upload procedure"""

    for src in filelist:
        s3_key = str(to_s3_key(data_dir, src))
        local_path = str(src.resolve())

        if is_file_exists(s3client, BUCKET_NAME, s3_key):
            print(f"{src} already exists in S3. Skipping... ")
            continue

        with create_uploader_progress_bar(src) as progress:
            s3client.upload_file(local_path, BUCKET_NAME, s3_key, Callback=progress.update)


def cli(args: Namespace):

    files = get_filelist(args.data_directory)
    botocore_config = botocore.config.Config(max_pool_connections=MAX_CONCURRENCY)
    sts_client = boto3.client('sts', config=botocore_config)
    assumed_role_object = sts_client.assume_role(
        RoleArn = "arn:aws:iam::656606567507:role/UpdateS3Role",
        RoleSessionName = "AssumeRoleSession",
        DurationSeconds = 43200 # 12 hours
    )
    credentials=assumed_role_object['Credentials']

    s3resource = boto3.resource('s3',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
    )
    s3client = s3resource.meta.client

    if args.debug:
        boto3.set_stream_logger('')

    if args.dry_run:
        paths = [(src, to_s3_key(args.data_directory, src)) for src in files]

        for src, dst in paths:
            print(f"{src} -> s3://{BUCKET_NAME}/{dst}")

    else:
        sync_files(s3client, args.data_directory, files)
