from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Sequence

import boto3
import botocore
from tqdm import tqdm

from ceti.whaletag import sha256sum

# TODO: (nikolay) set this to the project default bucket.
BUCKET_NAME = 'ceti-test-nikolay'
MAX_CONCURRENCY = 20
INGESTION_DATE_UTC = datetime.now(timezone.utc).strftime('%Y-%m-%d')


def get_s3_filenames(s3client, bucket_name: str) -> list:
    hashes = list()
    try:
        for key in s3client.list_objects(Bucket='bucket_name')['Contents']:
            hashes.append(Path(key['Key']).stem)
    finally:
        return hashes


def create_progress_bar(file_path: Path) -> tqdm:
    """Report upload progress and speed"""

    return tqdm(
        desc=f'uploading {file_path.name}',
        total=file_path.stat().st_size,
        unit='B',
        unit_scale=True,
        position=0,
    )


def get_filelist(src_dir: str) -> Sequence[Path]:
    """Create a list of files to be uploaded from the data directory"""

    path = Path(src_dir)
    return [p for p in sorted(path.glob('**/*')) if p.is_file()]


def to_s3_key(data_dir: str, src: Path, s3filenames: list) -> Path:
    """Create S3 key to address the file in the bucket"""

    filename = str(src.relative_to(data_dir))
    print(f"hashing {src}")
    hash = str(sha256sum(str(src.resolve())))
    if hash in s3filenames:
        return None
    filename = filename.replace(src.stem, hash)

    if not re.match(r".+\/.+", filename):
        # The file we are trying to upload is not
        # in the local folder that defines the device
        # that captured this file.
        # Therefore, it should be uploaded into
        # the "/unknown-device/" folder in S3
        filename = "unknown-device/"+filename

    key_path = Path('raw') / INGESTION_DATE_UTC / filename
    return key_path


def upload_files(s3client, data_dir: str, filelist: Sequence[Path], s3filenames: list) -> None:
    """Execute file upload procedure"""

    for src in filelist:
        s3_key = str(to_s3_key(data_dir, src, s3filenames))
        if not s3_key:
            continue
        local_path = str(src.resolve())

        with create_progress_bar(src) as progress:
            s3client.upload_file(local_path, BUCKET_NAME, s3_key, Callback=progress.update)


def cli(args: Namespace):

    files = get_filelist(args.data_directory)
    botocore_config = botocore.config.Config(max_pool_connections=MAX_CONCURRENCY)
    s3client = boto3.client('s3', config=botocore_config)
    s3filenames = get_s3_filenames(s3client, BUCKET_NAME)

    if args.debug:
        boto3.set_stream_logger('')

    if args.dry_run:
        for src in files:
            dst = to_s3_key(args.data_directory, src, s3filenames)
            print(f"{src} -> s3://{BUCKET_NAME}/{dst}")

    else:
        upload_files(s3client, args.data_directory, files, s3filenames)
