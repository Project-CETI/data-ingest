import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import boto3
import botocore
from tqdm import tqdm

# TODO: (nikolay) set this to the project default bucket.
BUCKET_NAME = 'ceti-test-nikolay'
MAX_CONCURRENCY = 20
INGESTION_DATE_UTC = datetime.now(timezone.utc).strftime('%Y-%m-%d')


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


def to_s3_key(data_dir: str, src: Path) -> Path:
    """Create S3 key to address the file in the bucket"""

    key_path = Path('raw') / INGESTION_DATE_UTC / src.relative_to(data_dir)

    return key_path


def upload_files(s3client, data_dir: str, filelist: Sequence[Path]) -> None:
    """Execute file upload procedure"""

    for src in filelist:
        s3_key = str(to_s3_key(data_dir, src))
        local_path = str(src.resolve())

        with create_progress_bar(src) as progress:
            s3client.upload_file(
                local_path, BUCKET_NAME, s3_key, Callback=progress.update)


def main():
    parser = argparse.ArgumentParser("Upload whale data to the AWS S3 cloud")

    parser.add_argument(
        "-t",
        "--dry-run",
        help="List source and destination paths, but do not upload anything",
        action="store_true")

    parser.add_argument(
        "-d",
        "--debug",
        help="Show debug messages during upload",
        action="store_true")

    parser.add_argument(
        "data_directory",
        type=Path,
        help="Path to the data directory where all the files are stored")

    args = parser.parse_args()
    files = get_filelist(args.data_directory)

    if args.debug:
        boto3.set_stream_logger('')

    if args.dry_run:
        for src in files:
            dst = to_s3_key(args.data_directory, src)
            print(f"{src} -> s3://{BUCKET_NAME}/{dst}")

    else:
        botocore_config = botocore.config.Config(max_pool_connections=MAX_CONCURRENCY)
        s3client = boto3.client('s3', config=botocore_config)

        upload_files(s3client, args.data_directory, files)


if __name__ == "__main__":
    main()
