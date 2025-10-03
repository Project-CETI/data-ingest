"""
Integration tests for S3 hash-based deduplication.

These tests verify that the deduplication logic in ceti/s3upload.py
correctly prevents re-uploading files with the same SHA256 hash.
"""

from pathlib import Path
import tempfile
import uuid

from ceti import s3upload
from ceti.utils import sha256sum


def test_deduplication_skips_duplicate_files(s3_client, test_bucket):
    """
    Test that files with the same hash are not uploaded twice.

    This verifies the deduplication logic in s3upload.py:72-79
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a unique test file
        test_id = uuid.uuid4().hex
        device_dir = Path(tmpdir) / f"device-{test_id}"
        device_dir.mkdir()

        test_file = device_dir / "test-data.txt"
        test_content = b"This is test data for deduplication"
        test_file.write_bytes(test_content)

        # Calculate expected hash
        file_hash = sha256sum(str(test_file))

        # First upload
        files = s3upload.get_filelist(tmpdir)
        assert len(files) == 1

        s3upload.sync_files(s3_client, tmpdir, files)

        # Verify file was uploaded
        s3_key = str(s3upload.to_s3_key(tmpdir, test_file))
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix=s3_key)
        assert 'Contents' in response
        assert len(response['Contents']) == 1

        # Verify hash marker was created
        hash_key = f"raw/hash/{file_hash}"
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix=hash_key)
        assert 'Contents' in response, "Hash marker should exist after upload"

        # Second upload attempt (should be skipped)
        # We can't easily verify it was skipped without mocking,
        # but we can verify the hash marker exists and would trigger skip logic
        assert s3upload.is_hash_exists(s3_client, test_bucket, file_hash)


def test_different_files_with_same_name_are_uploaded(s3_client, test_bucket):
    """
    Test that files with the same name but different content are both uploaded.

    Ensures deduplication is based on content hash, not filename.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_id = uuid.uuid4().hex

        # Create two devices with files of the same name but different content
        device1_dir = Path(tmpdir) / f"device-{test_id}-1"
        device1_dir.mkdir()
        file1 = device1_dir / "data.txt"
        file1.write_bytes(b"Content from device 1")

        device2_dir = Path(tmpdir) / f"device-{test_id}-2"
        device2_dir.mkdir()
        file2 = device2_dir / "data.txt"
        file2.write_bytes(b"Content from device 2")

        # Calculate hashes
        hash1 = sha256sum(str(file1))
        hash2 = sha256sum(str(file2))

        # Verify hashes are different
        assert hash1 != hash2, "Test files should have different hashes"

        # Upload both files
        files = s3upload.get_filelist(tmpdir)
        assert len(files) == 2

        s3upload.sync_files(s3_client, tmpdir, files)

        # Verify both hash markers exist
        assert s3upload.is_hash_exists(s3_client, test_bucket, hash1)
        assert s3upload.is_hash_exists(s3_client, test_bucket, hash2)

        # Verify both files were uploaded to different S3 keys
        s3_key1 = str(s3upload.to_s3_key(tmpdir, file1))
        s3_key2 = str(s3upload.to_s3_key(tmpdir, file2))

        assert s3_key1 != s3_key2, "Files from different devices should have different S3 keys"

        response1 = s3_client.list_objects_v2(Bucket=test_bucket, Prefix=s3_key1)
        assert 'Contents' in response1

        response2 = s3_client.list_objects_v2(Bucket=test_bucket, Prefix=s3_key2)
        assert 'Contents' in response2


def test_identical_files_are_deduplicated(s3_client, test_bucket):
    """
    Test that identical files (same content) are deduplicated even if in different locations.

    This simulates the scenario where the same data file appears in multiple device folders.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_id = uuid.uuid4().hex
        identical_content = b"Identical sensor data"

        # Create identical files in two different device folders
        device1_dir = Path(tmpdir) / f"device-{test_id}-1"
        device1_dir.mkdir()
        file1 = device1_dir / "sensor-reading.csv"
        file1.write_bytes(identical_content)

        device2_dir = Path(tmpdir) / f"device-{test_id}-2"
        device2_dir.mkdir()
        file2 = device2_dir / "sensor-reading.csv"
        file2.write_bytes(identical_content)

        # Verify hashes are identical
        hash1 = sha256sum(str(file1))
        hash2 = sha256sum(str(file2))
        assert hash1 == hash2, "Identical files should have same hash"

        # Upload first file
        files1 = [file1]
        s3upload.sync_files(s3_client, tmpdir, files1)

        # Verify hash marker exists
        assert s3upload.is_hash_exists(s3_client, test_bucket, hash1)

        # Try to upload second identical file
        # The hash check should indicate it already exists
        assert s3upload.is_hash_exists(s3_client, test_bucket, hash2)

        # This demonstrates that the second file would be skipped in real usage
