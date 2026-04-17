from pathlib import Path
import shutil
import tempfile
import uuid

from ceti import s3upload

TEST_DATA_DIR = Path(__file__).parent.resolve() / "test-data"
TEST_FILES = sorted(TEST_DATA_DIR.glob('**/device-*/file*.txt'))
SESSION_ID = uuid.uuid4().hex


def test_get_filelist():
    files = s3upload.get_filelist(str(TEST_DATA_DIR))

    for f in TEST_FILES:
        assert f in files


def test_file_upload(s3_mock):
    with tempfile.TemporaryDirectory() as tmpdir:
        dst_dir = str(Path(tmpdir) / SESSION_ID)
        shutil.copytree(TEST_DATA_DIR, dst_dir)

        files = s3upload.get_filelist(tmpdir)
        s3upload.sync_files(s3_mock, tmpdir, files)


def test_dedup_skips_existing(s3_mock):
    """Uploading the same files twice should skip on the second pass."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dst_dir = str(Path(tmpdir) / SESSION_ID)
        shutil.copytree(TEST_DATA_DIR, dst_dir)

        files = s3upload.get_filelist(tmpdir)
        s3upload.sync_files(s3_mock, tmpdir, files)
        s3upload.sync_files(s3_mock, tmpdir, files)

        objects = s3_mock.list_objects(Bucket="ceti-data-test")
        keys = [obj["Key"] for obj in objects.get("Contents", [])]
        hash_keys = [k for k in keys if k.startswith("raw/hash/")]
        assert len(hash_keys) == len(files)
