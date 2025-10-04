#!/bin/bash
# Whale Tag Mockup initialization script
# Generates realistic whale tag data structure for testing
# SSH server and DHCP client are pre-installed in the Docker image

set -e

echo "Initializing whale tag mockup..."

# Run DHCP client to get IP from router (macvlan mode only)
# In bridge/host mode, skip DHCP and use Docker-assigned IP
if [ "$NETWORK_MODE" = "macvlan" ]; then
    # Macvlan mode - request DHCP lease from router
    echo "Macvlan mode - requesting DHCP lease..."
    if timeout 5 dhcpcd -1 eth0 2>&1 | grep -q "leased"; then
        echo "DHCP lease obtained: $(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | head -1)"
    else
        echo "DHCP request failed (using Docker-assigned IP)"
    fi
else
    # Bridge or host mode - skip DHCP
    echo "Bridge mode - using Docker-assigned IP"
fi

# Create user pi with password ceticeti (if not exists)
if ! id pi > /dev/null 2>&1; then
    adduser -D -s /bin/bash pi
    echo "pi:${WHALETAG_PASSWORD:-ceticeti}" | chpasswd
fi

# Ensure /data directory ownership
chown pi:pi /data

# Check if data already exists (for faster restarts)
if [ -f /data/data_battery.csv ] && [ -f /data/logs/syslog ]; then
    echo "Existing whale tag data found - skipping generation"
    echo "To regenerate data, remove the Docker volume:"
    echo "  docker volume rm data-ingest_whaletag-data data-ingest_whaletag-backup"
elif [ -f /backup/mockup-data.tar.gz ]; then
    echo "Data was cleaned - restoring from backup..."
    echo "(Extracting ~500MB from compressed backup, ~10 seconds)"
    cd /data
    tar -xzf /backup/mockup-data.tar.gz
    chown -R pi:pi /data
    echo "✓ Data restored successfully!"
else
    echo "Generating realistic whale tag data files..."
    echo "(This takes ~5 minutes on first run, but persists across container restarts)"

    # Base timestamp: Jan 4, 2024 00:00:00 UTC
    BASE_EPOCH_S=1704384000
    BASE_EPOCH_MS=1704384000000

    # Switch to pi user for file generation (using bash not sh)
    su - pi -s /bin/bash <<'EOSU'
cd /data

# Base timestamps
BASE_EPOCH_S=1704384000
BASE_EPOCH_MS=1704384000000

#=============================================================================
# AUDIO FILES (~200MB total)
#=============================================================================
echo "Creating audio files..."

# FLAC files (5 files x 20MB = 100MB)
for i in 0 1 2 3 4; do
    epoch_ms=$((BASE_EPOCH_MS + i * 3600000))  # 1 hour apart
    dd if=/dev/urandom of="${epoch_ms}.flac" bs=1M count=20 2>/dev/null
done

# RAW files (3 files x 15MB = 45MB)
for i in 5 6 7; do
    epoch_ms=$((BASE_EPOCH_MS + i * 3600000))
    dd if=/dev/urandom of="${epoch_ms}.raw" bs=1M count=15 2>/dev/null
done

#=============================================================================
# SINGLE CSV FILES (~10MB total)
#=============================================================================
echo "Creating single CSV files..."

# data_battery.csv (1MB)
{
    echo "Timestamp_us,Voltage_mV,Current_mA,Temperature_C,StateOfCharge_pct,RemainingCapacity_mAh"
    for i in $(seq 1 20000); do
        ts=$((BASE_EPOCH_S * 1000000 + i * 5000000))
        voltage=$((4100 + RANDOM % 100))
        current=$((500 + RANDOM % 200))
        temp=$((20 + RANDOM % 15))
        soc=$((95 - i / 200))
        cap=$((3000 - i / 10))
        echo "$ts,$voltage,$current,$temp,$soc,$cap"
    done
} > data_battery.csv

# data_light.csv (500KB)
{
    echo "Timestamp_us,Light_lux"
    for i in $(seq 1 15000); do
        ts=$((BASE_EPOCH_S * 1000000 + i * 10000000))
        lux=$((100 + RANDOM % 50000))
        echo "$ts,$lux"
    done
} > data_light.csv

# data_pressure_temperature.csv (1MB)
{
    echo "Timestamp_us,Pressure_Pa,Temperature_C"
    for i in $(seq 1 25000); do
        ts=$((BASE_EPOCH_S * 1000000 + i * 4000000))
        pressure=$((101325 + RANDOM % 50000))
        temp=$((18 + RANDOM % 5))
        echo "$ts,$pressure,$temp"
    done
} > data_pressure_temperature.csv

# data_gps.csv (500KB)
{
    echo "Timestamp_us,Latitude,Longitude,Altitude_m,Speed_mps,Satellites,HDOP"
    for i in $(seq 1 10000); do
        ts=$((BASE_EPOCH_S * 1000000 + i * 15000000))
        # Dominica is around 15.3N, -61.4W
        lat="15.$((3000 + i % 10000))"
        lon="-61.$((4000 + i % 10000))"
        alt=$((0 + RANDOM % 100))
        speed=$((RANDOM % 10))
        sats=$((8 + RANDOM % 4))
        hdop="0.$((80 + RANDOM % 100))"
        echo "$ts,$lat,$lon,$alt,$speed,$sats,$hdop"
    done
} > data_gps.csv

# data_state.csv (100KB)
{
    echo "Timestamp_us,State,Notes"
    states=("IDLE" "RECORDING" "SURFACING" "TRANSMITTING" "SLEEPING")
    for i in $(seq 1 2000); do
        ts=$((BASE_EPOCH_S * 1000000 + i * 60000000))
        state=${states[$((RANDOM % 5))]}
        echo "$ts,$state,"
    done
} > data_state.csv

# data_audio_status.csv (1MB)
{
    echo "Timestamp [us],RTC Count,Notes,Overflow,Overflow Detection Location,Start Writing,Done Writing,See SPI Block"
    for i in $(seq 1 25000); do
        ts=$((BASE_EPOCH_S * 1000000 + i * 5000000))
        rtc=$((i * 192000))
        overflow=$((RANDOM % 100 < 1 ? 1 : 0))
        echo "$ts,$rtc,,$overflow,,,,"
    done
} > data_audio_status.csv

# data_systemMonitor.csv (2MB)
{
    echo "CPU all [%],CPU 0 [%],CPU 1 [%],CPU 2 [%],CPU 3 [%],RAM used [MB],RAM free [MB],Swap used [MB],Data partition used [GB],Data partition free [GB],CPU temp [C],GPU temp [C]"
    for i in $(seq 1 35000); do
        cpu_all=$((20 + RANDOM % 60))
        cpu0=$((10 + RANDOM % 70))
        cpu1=$((10 + RANDOM % 70))
        cpu2=$((10 + RANDOM % 70))
        cpu3=$((10 + RANDOM % 70))
        ram_used=$((200 + RANDOM % 300))
        ram_free=$((200 + RANDOM % 200))
        swap=$((RANDOM % 50))
        disk_used=$((10 + i / 3500))
        disk_free=$((50 - i / 3500))
        temp_cpu=$((45 + RANDOM % 20))
        temp_gpu=$((40 + RANDOM % 25))
        echo "$cpu_all,$cpu0,$cpu1,$cpu2,$cpu3,$ram_used,$ram_free,$swap,$disk_used,$disk_free,$temp_cpu,$temp_gpu"
    done
} > data_systemMonitor.csv

# burnwire_timeout_start_time_s.csv (10KB)
{
    echo "Timestamp_us,Burnwire_timeout_start_time_s"
    echo "$((BASE_EPOCH_S * 1000000)),$((BASE_EPOCH_S + 86400))"
} > burnwire_timeout_start_time_s.csv

#=============================================================================
# MULTI-FILE CSV DATASETS WITH COUNTERS (~250MB total)
#=============================================================================
echo "Creating multi-file CSV datasets..."

# IMU quaternion files (2 files x 25MB = 50MB) - ETA: ~30sec per file
for file_idx in 0 1; do
    echo "  Creating data_imu_quat_$(printf '%02d' $file_idx).csv (file $((file_idx + 1))/2)..."
    {
        echo "Capture_Timestamp_us,Read_Timestamp_us,RTC Count,Notes,Quat_i,Quat_j,Quat_k,Quat_Re,Quat_accuracy"
        for i in $(seq 1 500000); do
            cap_ts=$((BASE_EPOCH_S * 1000000 + i * 1000 + file_idx * 500000000))
            read_ts=$((cap_ts + 100))
            rtc=$((i * 20))
            # Simplified quaternion values (normalized random values)
            qi="0.$((RANDOM % 1000000))"
            qj="0.$((RANDOM % 1000000))"
            qk="0.$((RANDOM % 1000000))"
            qr="0.$((RANDOM % 1000000))"
            acc=$((RANDOM % 3))
            echo "$cap_ts,$read_ts,$rtc,,$qi,$qj,$qk,$qr,$acc"
        done
    } > "data_imu_quat_$(printf '%02d' $file_idx).csv"
    echo "  ✓ Completed data_imu_quat_$(printf '%02d' $file_idx).csv"
done

# IMU accelerometer files (2 files x 25MB = 50MB) - ETA: ~1min per file
for file_idx in 0 1; do
    echo "  Creating data_imu_accel_$(printf '%02d' $file_idx).csv (file $((file_idx + 1))/2)..."
    {
        echo "Capture_Timestamp_us,Read_Timestamp_us,RTC Count,Notes,Accel_x_raw,Accel_y_raw,Accel_z_raw,Accel_status"
        for i in $(seq 1 500000); do
            cap_ts=$((BASE_EPOCH_S * 1000000 + i * 400 + file_idx * 200000000))
            read_ts=$((cap_ts + 50))
            rtc=$((i * 50))
            ax=$((RANDOM % 4096 - 2048))
            ay=$((RANDOM % 4096 - 2048))
            az=$((RANDOM % 4096 - 2048))
            status=0
            echo "$cap_ts,$read_ts,$rtc,,$ax,$ay,$az,$status"
        done
    } > "data_imu_accel_$(printf '%02d' $file_idx).csv"
    echo "  ✓ Completed data_imu_accel_$(printf '%02d' $file_idx).csv"
done

# IMU gyroscope file (1 file x 25MB) - ETA: ~1min
echo "  Creating data_imu_gyro_00.csv..."
{
    echo "Capture_Timestamp_us,Read_Timestamp_us,RTC Count,Notes,Gyro_x_raw,Gyro_y_raw,Gyro_z_raw,Gyro_status"
    for i in $(seq 1 500000); do
        cap_ts=$((BASE_EPOCH_S * 1000000 + i * 400))
        read_ts=$((cap_ts + 50))
        rtc=$((i * 50))
        gx=$((RANDOM % 4096 - 2048))
        gy=$((RANDOM % 4096 - 2048))
        gz=$((RANDOM % 4096 - 2048))
        status=0
        echo "$cap_ts,$read_ts,$rtc,,$gx,$gy,$gz,$status"
    done
} > data_imu_gyro_00.csv
echo "  ✓ Completed data_imu_gyro_00.csv"

# IMU magnetometer file (1 file x 25MB) - ETA: ~1min
echo "  Creating data_imu_mag_00.csv..."
{
    echo "Capture_Timestamp_us,Read_Timestamp_us,RTC Count,Notes,Mag_x_raw,Mag_y_raw,Mag_z_raw,Mag_status"
    for i in $(seq 1 500000); do
        cap_ts=$((BASE_EPOCH_S * 1000000 + i * 400))
        read_ts=$((cap_ts + 50))
        rtc=$((i * 50))
        mx=$((RANDOM % 4096 - 2048))
        my=$((RANDOM % 4096 - 2048))
        mz=$((RANDOM % 4096 - 2048))
        status=0
        echo "$cap_ts,$read_ts,$rtc,,$mx,$my,$mz,$status"
    done
} > data_imu_mag_00.csv
echo "  ✓ Completed data_imu_mag_00.csv"

# ECG files (2 files x 25MB = 50MB) - ETA: ~2min per file
for file_idx in 0 1; do
    echo "  Creating data_ecg_$(printf '%02d' $file_idx).csv (file $((file_idx + 1))/2)..."
    {
        echo "Sample Index,ECG,Leads-Off-P,Leads-Off-N"
        for i in $(seq 1 1000000); do
            idx=$((i + file_idx * 1000000))
            ecg=$((32768 + RANDOM % 1000 - 500))
            lop=0
            lon=0
            echo "$idx,$ecg,$lop,$lon"
        done
    } > "data_ecg_$(printf '%02d' $file_idx).csv"
    echo "  ✓ Completed data_ecg_$(printf '%02d' $file_idx).csv"
done

#=============================================================================
# METADATA FILES (~1MB total)
#=============================================================================
echo "Creating metadata files..."

# data_config_<timestamp>.txt
cat > "data_config_${BASE_EPOCH_S}.txt" <<EOF
# CETI Whale Tag Configuration
# Deployment: Jan 4, 2024
# Location: Dominica, Eastern Caribbean

[audio]
sample_rate = 96000
bit_depth = 24
channels = 4
flac_compression = 5

[imu]
quaternion_rate = 20
accel_rate = 50
gyro_rate = 50
mag_rate = 50

[sensors]
battery_rate = 0.2
light_rate = 0.1
pressure_rate = 1.0
ecg_rate = 1000

[system]
log_level = INFO
cpu_affinity = 1,2,3
storage_threshold_gb = 1

[mission]
start_delay_s = 60
burnwire_timeout_s = 86400
max_depth_m = 500
EOF

# data_tag_info_<timestamp>.yaml
cat > "data_tag_info_${BASE_EPOCH_S}.yaml" <<EOF
tag_info:
  hardware_version: "v2.2"
  software_version: "2.5.0"
  mac_address: "b8:27:eb:12:34:56"
  serial_number: "WT2024-001"
  deployment:
    date: "2024-01-04T00:00:00Z"
    location: "Dominica, Eastern Caribbean"
    water_body: "Caribbean Sea"
    researcher: "CETI Team"
  sensors:
    audio:
      type: "AD7768-4"
      channels: 4
      max_sample_rate: 192000
    imu:
      type: "BNO086"
      axes: 9
    pressure:
      type: "MS5837"
      max_depth: 500
    battery:
      type: "LiPo"
      capacity_mah: 3000
      voltage_nominal: 3.7
EOF

#=============================================================================
# LOGS DIRECTORY (~40MB)
#=============================================================================
echo "Creating logs directory..."
mkdir -p logs

# Generate realistic syslog entries using Python (FAST!)
echo "  Creating logs/syslog (800k lines, ~40MB)..."
python3 /generate-syslog.py 800000 > logs/syslog
echo "  ✓ Completed logs/syslog"

#=============================================================================
# FALSE POSITIVES - Directories that should NOT be downloaded
#=============================================================================
echo "Creating system directories (false positives)..."

# swap directory with swapfile (should be excluded from download)
mkdir -p swap
dd if=/dev/zero of=swap/swapfile bs=1M count=10 2>/dev/null
chmod 600 swap/swapfile

# lost+found directory (filesystem recovery, should be excluded)
mkdir -p lost+found
chmod 700 lost+found
# Add some fake recovered file fragments
echo "corrupted data fragment" > lost+found/#12345
echo "partial file recovery" > lost+found/#67890

echo ""
echo "========================================="
echo "Data generation complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "  Audio files:      8 files  (~155MB)"
echo "  CSV files:        8 single + 10 multi-file (~60MB + ~250MB)"
echo "  Metadata:         2 files  (~1MB)"
echo "  Logs:             1 file   (~40MB)"
echo "  System dirs:      swap/, lost+found/"
echo ""
echo "Total size: ~510MB"
echo ""
EOSU

# Hostname is already set by Docker Compose
# No need to set it again (and would require privileged mode)

echo "========================================="
echo "Whale tag mockup initialized!"
echo "========================================="
echo "Hostname: $(hostname)"
echo "SSH user: pi"
echo "SSH password: ${WHALETAG_PASSWORD:-ceticeti}"
echo "Data directory: /data"
echo ""
echo "File structure:"
su - pi -c "ls -lh /data | head -25"
echo "..."
echo ""
echo "Total size:"
su - pi -c "du -sh /data"
echo ""

# Create compressed backup for quick restoration after testing cleanup
if [ ! -f /backup/mockup-data.tar.gz ]; then
    echo ""
    echo "Creating backup for quick restoration after cleanup tests..."
    cd /data
    tar -czf /backup/mockup-data.tar.gz \
        --exclude='lost+found' \
        *.flac *.raw *.csv *.txt *.yaml logs/ swap/ 2>/dev/null || true
    chmod 600 /backup/mockup-data.tar.gz
    echo "✓ Backup created in separate volume (not in /data)"
    du -sh /backup/mockup-data.tar.gz
fi

echo ""
echo "========================================="
echo "Ready for testing!"
echo "========================================="
echo ""
echo "Test workflow:"
echo "  1. Download: ceti whaletag -t <container_ip>"
echo "  2. Clean:    ceti whaletag -ct <container_ip>"
echo "  3. Restart:  docker restart wt-b827eb123456"
echo "  4. → Data auto-restores from backup in ~10 seconds"
fi

# Start SSH server in foreground
echo "Starting SSH server..."
exec /usr/sbin/sshd -D
