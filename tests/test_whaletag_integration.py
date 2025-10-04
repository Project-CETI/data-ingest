"""
Whale Tag Integration Tests

These tests require a whale tag simulator or real hardware to be available.
They are excluded from default pytest runs via pytest markers.

To run these tests:
  make test-whaletag  # Starts simulator, runs tests, stops simulator
  pytest -m whaletag  # Run with existing simulator/hardware
"""

import os
import pytest
import paramiko


# Whale tag connection parameters
# For simulator: get IP with docker inspect
WHALETAG_HOSTNAME = os.getenv('WHALETAG_HOSTNAME', 'wt-b827eb123456')
WHALETAG_HOST = os.getenv('WHALETAG_HOST')  # If not set, will auto-detect from Docker
WHALETAG_PORT = int(os.getenv('WHALETAG_PORT', '22'))  # Standard SSH port
WHALETAG_USERNAME = 'pi'
WHALETAG_PASSWORD = os.getenv('WHALETAG_PASSWORD', 'ceticeti')
WHALETAG_HOSTNAME_PATTERN = r'^wt-[a-z0-9]{6,}$'


def get_whaletag_ip():
    """Get IP address of whale tag simulator container"""
    if WHALETAG_HOST:
        return WHALETAG_HOST

    # Auto-detect container IP
    import subprocess
    try:
        result = subprocess.run(
            ['docker', 'inspect', '-f',
             '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
             WHALETAG_HOSTNAME],
            capture_output=True, text=True, check=True
        )
        ip = result.stdout.strip()
        if ip:
            return ip
    except subprocess.CalledProcessError:
        pass

    raise RuntimeError(
        f"Cannot find whale tag simulator. "
        f"Set WHALETAG_HOST or ensure container '{WHALETAG_HOSTNAME}' is running."
    )


@pytest.fixture
def ssh_client():
    """Create SSH client connection to whale tag"""
    host = get_whaletag_ip()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=WHALETAG_PORT,
        username=WHALETAG_USERNAME,
        password=WHALETAG_PASSWORD,
        timeout=10
    )
    yield client
    client.close()


@pytest.mark.whaletag
def test_ssh_connection(ssh_client):
    """Test SSH connection to whale tag"""
    stdin, stdout, stderr = ssh_client.exec_command('echo "test"')
    output = stdout.read().decode().strip()
    assert output == 'test', "SSH command execution failed"


@pytest.mark.whaletag
def test_hostname_pattern(ssh_client):
    """Test that hostname matches wt-* pattern"""
    import re
    stdin, stdout, stderr = ssh_client.exec_command('hostname')
    hostname = stdout.read().decode().strip()
    assert re.match(WHALETAG_HOSTNAME_PATTERN, hostname), \
        f"Hostname '{hostname}' does not match pattern '{WHALETAG_HOSTNAME_PATTERN}'"


@pytest.mark.whaletag
def test_data_directory_exists(ssh_client):
    """Test that /data directory exists"""
    stdin, stdout, stderr = ssh_client.exec_command('test -d /data && echo "exists"')
    output = stdout.read().decode().strip()
    assert output == 'exists', "/data directory does not exist"


@pytest.mark.whaletag
def test_data_directory_has_files(ssh_client):
    """Test that /data directory contains realistic whale tag files"""
    stdin, stdout, stderr = ssh_client.exec_command('ls -1 /data')
    files = stdout.read().decode().strip().split('\n')
    assert len(files) > 0, "/data directory is empty"

    # Check for realistic whale tag file patterns
    file_str = ' '.join(files)

    # Audio files: <epoch_ms>.flac or <epoch_ms>.raw
    assert any(f.endswith('.flac') or f.endswith('.raw') for f in files), \
        "No audio files (.flac/.raw) found in /data"

    # CSV sensor data files
    assert any(f.startswith('data_') and f.endswith('.csv') for f in files), \
        "No CSV sensor files (data_*.csv) found in /data"

    # Metadata files
    assert any(f.startswith('data_config_') and f.endswith('.txt') for f in files), \
        "No config metadata files found in /data"

    # Logs directory
    assert 'logs' in files, "logs/ directory not found in /data"

    # False positives (should exist but not be downloaded)
    assert 'swap' in files, "swap/ directory not found (false positive test)"
    assert 'lost+found' in files, "lost+found/ directory not found (false positive test)"


@pytest.mark.whaletag
def test_sftp_download(ssh_client):
    """Test SFTP file download from whale tag"""
    import tempfile
    from pathlib import Path

    sftp = ssh_client.open_sftp()

    # List files in /data
    files = sftp.listdir('/data')
    assert len(files) > 0, "/data directory is empty"

    # Download a realistic audio file (should be large)
    audio_files = [f for f in files if f.endswith('.flac') or f.endswith('.raw')]
    assert len(audio_files) > 0, "No audio files to download"

    remote_file = f'/data/{audio_files[0]}'

    with tempfile.TemporaryDirectory() as tmpdir:
        local_file = Path(tmpdir) / audio_files[0]
        sftp.get(remote_file, str(local_file))
        assert local_file.exists(), f"Failed to download {remote_file}"
        assert local_file.stat().st_size > 1024 * 1024, \
            f"Downloaded file too small: {local_file.stat().st_size} bytes (expected >1MB)"

    sftp.close()


@pytest.mark.whaletag
def test_sftp_recursive_directory_listing(ssh_client):
    """Test SFTP can list directories recursively (logs/, swap/, etc.)"""
    sftp = ssh_client.open_sftp()

    # List /data directory
    files = sftp.listdir('/data')
    assert 'logs' in files, "logs/ directory not found in SFTP listing"

    # List logs/ subdirectory
    log_files = sftp.listdir('/data/logs')
    assert 'syslog' in log_files, "syslog not found in /data/logs"

    # Verify we can stat the syslog file
    stat = sftp.stat('/data/logs/syslog')
    assert stat.st_size > 1024 * 1024, "syslog file should be >1MB"

    sftp.close()


@pytest.mark.whaletag
def test_sftp_download_csv_file(ssh_client):
    """Test SFTP download of CSV sensor data files"""
    import tempfile
    from pathlib import Path

    sftp = ssh_client.open_sftp()

    # Find a CSV file
    files = sftp.listdir('/data')
    csv_files = [f for f in files if f.endswith('.csv')]
    assert len(csv_files) > 0, "No CSV files found"

    remote_file = f'/data/{csv_files[0]}'

    with tempfile.TemporaryDirectory() as tmpdir:
        local_file = Path(tmpdir) / csv_files[0]
        sftp.get(remote_file, str(local_file))

        assert local_file.exists(), f"Failed to download {remote_file}"

        # Verify it's a valid CSV by checking first line has comma-separated values
        with open(local_file) as f:
            first_line = f.readline()
            assert ',' in first_line, "Downloaded CSV file has invalid format"

    sftp.close()


@pytest.mark.whaletag
def test_user_permissions(ssh_client):
    """Test that user pi can access /data directory"""
    stdin, stdout, stderr = ssh_client.exec_command('whoami')
    user = stdout.read().decode().strip()
    assert user == 'pi', f"Expected user 'pi', got '{user}'"

    # Test write permission
    stdin, stdout, stderr = ssh_client.exec_command('touch /data/.test && rm /data/.test && echo "success"')
    output = stdout.read().decode().strip()
    assert output == 'success', "User pi does not have write permission to /data"


@pytest.mark.whaletag
def test_file_ownership(ssh_client):
    """Test that files in /data are owned by pi:pi"""
    stdin, stdout, stderr = ssh_client.exec_command('ls -la /data/*.flac /data/*.csv 2>/dev/null | head -5')
    output = stdout.read().decode()

    # Parse ls -la output and check ownership
    for line in output.strip().split('\n'):
        if not line or line.startswith('total'):
            continue
        parts = line.split()
        if len(parts) >= 3:
            owner = parts[2]  # 3rd column is owner
            group = parts[3]  # 4th column is group
            assert owner == 'pi', f"File not owned by pi: {line}"
            assert group == 'pi', f"File not in pi group: {line}"


@pytest.mark.whaletag
def test_sudo_permissions(ssh_client):
    """Test that user pi has passwordless sudo access"""
    # Test sudo without password (required for ceti whaletag -ct cleanup)
    stdin, stdout, stderr = ssh_client.exec_command('sudo -n whoami')
    output = stdout.read().decode().strip()
    error = stderr.read().decode().strip()

    assert output == 'root', f"sudo failed: {error}"
    assert 'password' not in error.lower(), "sudo requires password (should be passwordless)"


@pytest.mark.whaletag
def test_false_positives_exist(ssh_client):
    """Test that false positive directories exist (swap, lost+found)"""
    # These directories should exist but should NOT be downloaded by ceti whaletag
    stdin, stdout, stderr = ssh_client.exec_command('test -d /data/swap && echo "swap_exists"')
    output = stdout.read().decode().strip()
    assert output == 'swap_exists', "swap/ directory should exist as false positive"

    stdin, stdout, stderr = ssh_client.exec_command('test -d /data/lost+found && echo "lost_exists"')
    output = stdout.read().decode().strip()
    assert output == 'lost_exists', "lost+found/ directory should exist as false positive"


@pytest.mark.whaletag
def test_realistic_file_sizes(ssh_client):
    """Test that files have realistic sizes (not empty placeholders)"""
    # Check audio files have realistic size (>10MB)
    stdin, stdout, stderr = ssh_client.exec_command('ls -lh /data/*.flac /data/*.raw 2>/dev/null | head -3')
    output = stdout.read().decode()

    sizes = []
    for line in output.strip().split('\n'):
        if not line or line.startswith('total'):
            continue
        parts = line.split()
        if len(parts) >= 5:
            size_str = parts[4]  # 5th column is size
            sizes.append(size_str)

    assert len(sizes) > 0, "No audio files found"

    # Check that at least one file is >10M
    large_files = [s for s in sizes if 'M' in s or 'G' in s]
    assert len(large_files) > 0, f"Audio files should be >10MB, got: {sizes}"


@pytest.mark.whaletag
def test_multi_file_csv_datasets(ssh_client):
    """Test that multi-file CSV datasets exist with counter suffixes"""
    # Check for IMU files with _00, _01 suffixes
    stdin, stdout, stderr = ssh_client.exec_command('ls /data/data_imu_*_00.csv 2>/dev/null | wc -l')
    count = int(stdout.read().decode().strip())
    assert count > 0, "No multi-file IMU datasets found (data_imu_*_00.csv)"

    # Check for ECG files with counter
    stdin, stdout, stderr = ssh_client.exec_command('ls /data/data_ecg_*.csv 2>/dev/null | wc -l')
    count = int(stdout.read().decode().strip())
    assert count > 0, "No ECG datasets found (data_ecg_*.csv)"


@pytest.mark.whaletag
def test_logs_directory_with_syslog(ssh_client):
    """Test that logs directory contains syslog file"""
    stdin, stdout, stderr = ssh_client.exec_command('test -f /data/logs/syslog && echo "exists"')
    output = stdout.read().decode().strip()
    assert output == 'exists', "logs/syslog file not found"

    # Check syslog has realistic size (should be large - 800k lines)
    stdin, stdout, stderr = ssh_client.exec_command('wc -l /data/logs/syslog')
    line_count = int(stdout.read().decode().split()[0])
    assert line_count > 100000, f"syslog should have >100k lines, got {line_count}"


@pytest.mark.whaletag
def test_ssh_server_running(ssh_client):
    """Test that SSH server is running and accessible"""
    # Check sshd process is running
    stdin, stdout, stderr = ssh_client.exec_command('ps aux | grep sshd | grep -v grep')
    output = stdout.read().decode()
    assert 'sshd' in output, "SSH server (sshd) is not running"

    # Verify we can execute commands (already proven by ssh_client fixture working)
    stdin, stdout, stderr = ssh_client.exec_command('echo "ssh_works"')
    result = stdout.read().decode().strip()
    assert result == 'ssh_works', "SSH command execution failed"


@pytest.mark.whaletag
def test_backup_exists(ssh_client):
    """Test that backup archive exists in /backup volume"""
    stdin, stdout, stderr = ssh_client.exec_command('test -f /backup/mockup-data.tar.gz && echo "exists"')
    output = stdout.read().decode().strip()
    assert output == 'exists', "Backup file /backup/mockup-data.tar.gz not found"

    # Check backup size is reasonable (should be ~200MB compressed)
    stdin, stdout, stderr = ssh_client.exec_command('du -h /backup/mockup-data.tar.gz')
    size_output = stdout.read().decode().strip()
    size_str = size_output.split()[0]
    assert 'M' in size_str or 'G' in size_str, \
        f"Backup file too small: {size_str} (expected >100M)"


@pytest.mark.whaletag
def test_data_cleanup_and_restore():
    """Test data cleanup with sudo rm and restore from backup on container restart"""
    import subprocess
    import time

    # Get container name
    container_name = os.getenv('WHALETAG_HOSTNAME', 'wt-b827eb123456')

    # Step 1: Verify data exists before cleanup
    result = subprocess.run(
        ['docker', 'exec', container_name, 'ls', '/data'],
        capture_output=True, text=True
    )
    initial_files = result.stdout.strip().split('\n')
    assert len(initial_files) > 5, "Not enough files in /data before cleanup"
    assert any('.flac' in f or '.csv' in f for f in initial_files), \
        "No data files found before cleanup"

    # Step 2: Clean data using sudo rm (simulates ceti whaletag -ct)
    # Need shell expansion for glob pattern
    subprocess.run(
        ['docker', 'exec', container_name, 'sh', '-c', 'sudo rm -rf /data/*.*'],
        check=True
    )

    # Verify data is cleaned (only directories remain)
    result = subprocess.run(
        ['docker', 'exec', container_name, 'ls', '/data'],
        capture_output=True, text=True
    )
    remaining_files = result.stdout.strip().split('\n')
    # Should only have directories left (logs, swap, lost+found)
    assert not any('.flac' in f or '.csv' in f for f in remaining_files), \
        "Data files still exist after cleanup"

    # Step 3: Restart container to trigger restore
    subprocess.run(['docker', 'restart', container_name], check=True)

    # Wait for container to restart and restore data
    time.sleep(15)

    # Step 4: Verify data is restored
    result = subprocess.run(
        ['docker', 'exec', container_name, 'ls', '/data'],
        capture_output=True, text=True
    )
    restored_files = result.stdout.strip().split('\n')
    assert len(restored_files) > 5, "Not enough files after restore"
    assert any('.flac' in f for f in restored_files), "Audio files not restored"
    assert any('.csv' in f for f in restored_files), "CSV files not restored"

    # Verify SSH server is running after restore
    time.sleep(2)
    result = subprocess.run(
        ['docker', 'exec', container_name, 'pgrep', 'sshd'],
        capture_output=True, text=True
    )
    assert result.returncode == 0, "SSH server not running after restore"
