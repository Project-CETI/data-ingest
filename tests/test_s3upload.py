from pathlib import Path
import shutil
import tempfile

import boto3

from ceti import s3upload

TEST_DATA_DIR = Path(__file__).parent.resolve() / "test-data"
TEST_FILES = sorted(TEST_DATA_DIR.glob('**/device-*/file*.txt'))


def test_get_filelist():
    files = s3upload.get_filelist(str(TEST_DATA_DIR))

    for f in TEST_FILES:
        assert f in files


def test_file_upload():
    with tempfile.TemporaryDirectory() as dst_dir:
        shutil.copytree(TEST_DATA_DIR, dst_dir, exist_ok=True)

        files = s3upload.get_filelist(dst_dir)
        s3client = boto3.client('s3')
        s3upload.sync_files(s3client, dst_dir, files)
