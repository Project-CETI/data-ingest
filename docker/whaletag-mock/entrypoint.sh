#!/bin/bash
set -e

HOSTNAME="wt-b827eb123456"
echo "$HOSTNAME" > /etc/hostname
hostname "$HOSTNAME"

mkdir -p /data/logs

# Sample audio-style files (small placeholders)
echo "FAKE_FLAC_1700000000000" > /data/1700000000000.flac
echo "FAKE_FLAC_1700000060000" > /data/1700000060000.flac

# Sample CSV sensor data
cat > /data/battery.csv <<'CSV'
timestamp_ms,voltage_mv,current_ma,soc_pct
1700000000000,3850,120,78
1700000010000,3848,118,77
1700000020000,3845,122,77
CSV

cat > /data/imu.csv <<'CSV'
timestamp_ms,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z
1700000000000,0.02,-0.01,9.81,0.001,0.002,-0.001
1700000010000,0.03,-0.02,9.80,0.002,0.001,-0.002
CSV

cat > /data/gps.csv <<'CSV'
timestamp_ms,lat,lon,alt_m,fix_quality
1700000000000,19.6725,-72.3208,0.5,1
1700000060000,19.6730,-72.3205,0.3,1
CSV

# Sample metadata
cat > /data/config.txt <<'TXT'
sample_rate=96000
channels=1
bit_depth=24
gain_db=20
TXT

# Sample syslog in /data/logs
for i in $(seq 1 100); do
  echo "$(date -d @$((1700000000 + i)) -u '+%b %d %H:%M:%S' 2>/dev/null || echo "Nov 14 22:$(printf '%02d' $((i%60))):$(printf '%02d' $((i%60)))")") $HOSTNAME kernel: sample log line $i" >> /data/logs/syslog
done

# False positives the real code should skip
mkdir -p /data/swap /data/lost+found
echo "swapfile" > /data/swap/swapfile
echo "orphan" > /data/lost+found/orphan

chown -R pi:pi /data

exec /usr/sbin/sshd -D -e
