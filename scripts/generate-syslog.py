#!/usr/bin/env python3
"""
Fast syslog generator for whale tag mockup
Generates 800k realistic log lines in ~2 seconds
"""

import sys

def generate_syslog(num_lines=800000):
    """Generate realistic syslog entries"""

    # Log message templates
    templates = [
        "cetiTagApp[1234]: Audio buffer written: {} samples",
        "cetiTagApp[1234]: IMU data logged: {} records",
        "cetiTagApp[1234]: Battery: {}%",
        "systemd[1]: Started session {}",
        "kernel: [{}.000000] random: crng init done",
        "cetiTagApp[1234]: Pressure: {} Pa",
        "cetiTagApp[1234]: Temperature: {}C",
        "sshd[5678]: Accepted publickey for pi from 192.168.1.{}",
        "cetiTagApp[1234]: State transition: RECORDING",
        "cetiTagApp[1234]: Free space: {} GB"
    ]

    # Header
    print("Jan  4 00:00:00 wt-b827eb123456 cetiTagApp[1234]: System initialization")
    print("Jan  4 00:00:01 wt-b827eb123456 kernel: [    0.000000] Booting Linux on physical CPU 0x0")

    # Generate log lines
    for i in range(1, num_lines + 1):
        hour = (i // 120000) % 24
        minute = (i // 2000) % 60
        second = (i // 33) % 60

        template_idx = i % 10
        template = templates[template_idx]

        # Format message with dynamic values
        if template_idx == 0:
            msg = template.format(i)
        elif template_idx == 1:
            msg = template.format(i)
        elif template_idx == 2:
            msg = template.format(max(50, 95 - i // 10000))
        elif template_idx == 3:
            msg = template.format(i // 1000)
        elif template_idx == 4:
            msg = template.format(i // 100)
        elif template_idx == 5:
            msg = template.format(101325 + (i * 137) % 50000)
        elif template_idx == 6:
            msg = template.format(18 + (i * 7) % 10)
        elif template_idx == 7:
            msg = template.format((i * 23) % 255)
        elif template_idx == 8:
            msg = "cetiTagApp[1234]: State transition: RECORDING"
        elif template_idx == 9:
            msg = template.format(max(10, 50 - i // 20000))

        print(f"Jan  4 {hour:02d}:{minute:02d}:{second:02d} wt-b827eb123456 {msg}")

if __name__ == "__main__":
    num_lines = int(sys.argv[1]) if len(sys.argv) > 1 else 800000
    generate_syslog(num_lines)
