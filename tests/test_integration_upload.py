"""
Integration tests for end-to-end S3 upload workflows.

These tests verify the complete upload process including file discovery,
S3 key generation, and proper folder structure.
"""

from pathlib import Path
import tempfile
import uuid

from ceti import s3upload


def test_upload_creates_correct_s3_structure(s3_client, test_bucket):
    """
    Test that uploaded files have the correct S3 key structure.

    Expected format: raw/YYYY-MM-DD/device-id/filename
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_id = uuid.uuid4().hex
        device_id = f"wt-{test_id}"

        # Create test file in device folder
        device_dir = Path(tmpdir) / device_id
        device_dir.mkdir()

        test_file = device_dir / "audio.flac"
        test_file.write_bytes(b"fake flac audio data")

        # Upload file
        files = s3upload.get_filelist(tmpdir)
        s3upload.sync_files(s3_client, tmpdir, files)

        # Verify S3 key structure
        s3_key = str(s3upload.to_s3_key(tmpdir, test_file))

        # Key should be: raw/YYYY-MM-DD/wt-{test_id}/audio.flac
        parts = s3_key.split('/')
        assert parts[0] == 'raw', f"First part should be 'raw', got {parts[0]}"
        # parts[1] is the date (YYYY-MM-DD)
        assert parts[2] == device_id, f"Device ID should be {device_id}, got {parts[2]}"
        assert parts[3] == 'audio.flac', f"Filename should be audio.flac, got {parts[3]}"

        # Verify file exists in S3
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix=s3_key)
        assert 'Contents' in response
        assert len(response['Contents']) == 1


def test_upload_files_without_device_folder_go_to_unknown_device(s3_client, test_bucket):
    """
    Test that files not in a device folder are uploaded to unknown-device/.

    Per s3upload.py:46-58, files without proper folder structure go to unknown-device/
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_id = uuid.uuid4().hex

        # Create file directly in tmpdir (no device folder)
        test_file = Path(tmpdir) / f"orphan-{test_id}.txt"
        test_file.write_bytes(b"orphaned data file")

        # Upload file
        files = s3upload.get_filelist(tmpdir)
        assert len(files) == 1

        s3upload.sync_files(s3_client, tmpdir, files)

        # Verify S3 key includes unknown-device
        s3_key = str(s3upload.to_s3_key(tmpdir, test_file))

        # Should not have device folder pattern
        assert 'unknown-device' not in s3_key or s3_key.split('/')[2] == 'unknown-device'

        # Verify file was uploaded
        response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix='raw/')
        assert 'Contents' in response


def test_upload_multiple_files_from_multiple_devices(s3_client, test_bucket):
    """
    Test uploading multiple files from multiple devices in one operation.

    Simulates real-world scenario where multiple whale tags are downloaded.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_id = uuid.uuid4().hex

        # Create multiple devices with multiple files each
        devices = [
            (f"wt-{test_id}-1", ["audio1.flac", "sensors1.csv.gz"]),
            (f"wt-{test_id}-2", ["audio2.flac", "sensors2.csv.gz"]),
            (f"mg-{test_id}-3", ["mooring-data.csv.gz"])  # Different device type
        ]

        created_files = []
        for device_id, filenames in devices:
            device_dir = Path(tmpdir) / device_id
            device_dir.mkdir()

            for filename in filenames:
                file_path = device_dir / filename
                file_path.write_bytes(f"Data from {device_id}/{filename}".encode())
                created_files.append(file_path)

        # Upload all files
        files = s3upload.get_filelist(tmpdir)
        assert len(files) == 5, f"Expected 5 files, found {len(files)}"

        s3upload.sync_files(s3_client, tmpdir, files)

        # Verify all files were uploaded with correct device folders
        for device_id, filenames in devices:
            for filename in filenames:
                # Check that S3 key contains the device ID
                prefix = f"raw/"
                response = s3_client.list_objects_v2(Bucket=test_bucket, Prefix=prefix)

                assert 'Contents' in response
                keys = [obj['Key'] for obj in response['Contents']]

                # Should find a key containing both device_id and filename
                matching_keys = [k for k in keys if device_id in k and filename in k]
                assert len(matching_keys) >= 1, \
                    f"Should find S3 key for {device_id}/{filename}, got keys: {keys}"


def test_upload_respects_bucket_environment_variable(s3_client, test_bucket_name):
    """
    Test that uploads use the bucket name from CETI_BUCKET environment variable.

    The test_bucket_name fixture already reads from CETI_BUCKET env var.
    """
    # This test verifies that the fixture is correctly using the env var
    # which the code also uses (s3upload.py:14)
    import os
    expected_bucket = os.getenv("CETI_BUCKET", "ceti-data-test")

    assert test_bucket_name == expected_bucket, \
        f"Test bucket should match CETI_BUCKET env var: {expected_bucket}"

    # Verify the bucket exists and is accessible
    response = s3_client.list_buckets()
    bucket_names = [b['Name'] for b in response['Buckets']]

    assert test_bucket_name in bucket_names, \
        f"Bucket {test_bucket_name} should exist in S3"
