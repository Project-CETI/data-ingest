from pathlib import Path
import shutil
import tempfile
import uuid

import boto3

from ceti import s3upload

TEST_DATA_DIR = Path(__file__).parent.resolve() / "test-data"
TEST_FILES = sorted(TEST_DATA_DIR.glob('**/device-*/file*.txt'))
SESSION_ID = uuid.uuid4().hex


def test_get_filelist():
    files = s3upload.get_filelist(str(TEST_DATA_DIR))

    for f in TEST_FILES:
        assert f in files


def test_file_upload():
    with tempfile.TemporaryDirectory() as tmpdir:
        dst_dir = str(Path(tmpdir) / SESSION_ID)
        shutil.copytree(TEST_DATA_DIR, dst_dir)

        files = s3upload.get_filelist(tmpdir)
        s3client = boto3.client('s3')
        s3upload.sync_files(s3client, tmpdir, files)
