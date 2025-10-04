# Testing Guide

This guide covers how to test the CETI data ingestion tools locally.

## Whale Tag Simulator

The whale tag simulator allows you to test `ceti whaletag` commands locally without physical hardware.

### Quick Start

```bash
# Start the simulator
make whaletag-up

# Run automated tests
make test-whaletag

# Stop the simulator
make whaletag-down
```

### Manual Testing

```bash
# Start simulator
make whaletag-up

# Get container IP
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' wt-b827eb123456)

# Test SSH connection
ssh pi@$CONTAINER_IP
# Password: ceticeti

# Inside the container, check test data
ls -la /data

# Exit SSH
exit

# Test with ceti whaletag command
ceti whaletag -t $CONTAINER_IP

# Stop simulator
make whaletag-down
```

### What Gets Simulated

The simulator creates a Docker container with:
- **Base Image**: Alpine Linux (~12 MB)
- **Network**: Docker bridge network (container gets its own IP)
- **SSH Server**: OpenSSH on port 22
- **User**: `pi` with password `ceticeti`
- **Hostname**: `wt-b827eb123456` (configurable via `.env.whaletag`)
- **Test Data**: Sample files in `/data/`:
  - Audio files (`.raw`, `.flac`)
  - Sensor data (CSV files)

### Configuration

Edit `.env.whaletag` to customize:

```bash
# Hostname of the simulated whale tag
WHALETAG_HOSTNAME=wt-b827eb123456

# SSH password for user 'pi'
WHALETAG_PASSWORD=ceticeti

# Network mode (bridge, host, or macvlan)
NETWORK_MODE=bridge
```

**Network Modes:**
- **bridge** (default): Container gets Docker bridge IP, accessible from host via container IP
- **host**: Container shares host network (may conflict with host SSH on port 22)
- **macvlan** (advanced): Container gets real LAN IP via DHCP, discoverable by `ceti whaletag -l` from other machines

### Running Tests

**Default pytest (excludes whale tag tests):**
```bash
pytest  # Whale tag tests are NOT run
```

**Run only whale tag tests:**
```bash
pytest -m whaletag
```

**Run all tests including whale tag:**
```bash
pytest -m ""
```

**Automated test workflow:**
```bash
make test-whaletag  # Starts simulator → runs tests → stops simulator
```

### Test Coverage

The whale tag integration tests verify:
- SSH connection to simulated tag
- Hostname pattern validation (`wt-*`)
- `/data` directory exists
- Test files present in `/data`
- SFTP file download
- User permissions for `pi` user

### Limitations

**What the simulator CAN test:**
- SSH/SFTP connectivity
- File download workflows (`ceti whaletag -t <IP>`)
- Hostname validation
- Data cleaning operations

**What the simulator CANNOT test (bridge mode):**
- Network discovery (`ceti whaletag -l` won't find containers on Docker bridge network)
- Real sensor data capture
- Actual whale tag firmware behavior
- Hardware-specific features

**Note:** In bridge mode (default), you must use `ceti whaletag -t <container-ip>` to connect directly. The `-l` discovery flag scans your LAN and won't find Docker bridge containers. For LAN discovery testing, use macvlan mode (see `.env.whaletag` configuration).

### Troubleshooting

**Simulator won't start:**
```bash
# Check Docker is running
docker ps

# View simulator logs
docker logs wt-b827eb123456
```

**Cannot connect via SSH:**
```bash
# Ensure simulator is running
docker ps | grep wt-b827eb123456

# Get container IP
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' wt-b827eb123456

# Check SSH server status inside container
docker exec wt-b827eb123456 ps aux | grep sshd
```

**Clean start:**
```bash
# Remove all simulator data and restart
make whaletag-clean
make whaletag-up
```

### Advanced Usage

**Access simulator shell:**
```bash
docker exec -it wt-b827eb123456 /bin/bash
```

**View container logs:**
```bash
docker logs wt-b827eb123456
```

**Inspect test data:**
```bash
docker exec wt-b827eb123456 ls -la /data
```

**Test whale tag commands:**
```bash
# Get container IP
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' wt-b827eb123456)

# Download data from tag
ceti whaletag -t $CONTAINER_IP

# Clean tag (destructive - removes all /data files)
ceti whaletag -ct $CONTAINER_IP
```
