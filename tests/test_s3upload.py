from pathlib import Path

from ceti import s3upload

TEST_DATA_DIR = Path(__file__).parent.resolve() / "test-data"
TEST_FILES = sorted(TEST_DATA_DIR.glob('**/device-*/file*.txt'))


def test_get_filelist():
    files = s3upload.get_filelist(str(TEST_DATA_DIR))

    for f in TEST_FILES:
        assert f in files
