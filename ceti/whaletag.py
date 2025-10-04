# This script is assumed to be running on a linux x86 computer
# while being attached to the same wireless network as a charged and
# running whale tag to pull the data from.

# All of the data will be pulled into the the forlder ./data
# Whale tags are embedded computers that automatically connect to a "ceti"
# wireless network. They also support Ethernet over USB protocol, but
# the phisical access to the USB port may be difficult to reach.

# Each whale tag has a a unique hostname of the format "wt-XXXXXXXXXXXX",
# where X are alphanumerics.

# To access a whale tag, connect using ssh on port 22.
# The username is "pi", the password is "ceticeti".

from argparse import Namespace
import asyncio
import ipaddress
import os
import re
import socket
import sys
import time
import netifaces

import findssh
import paramiko
from tqdm import tqdm

from ceti.utils import sha256sum


LOCAL_DATA_PATH = os.path.join(os.getcwd(), "data")
DEFAULT_USBGADGET_IPNETWORK = "192.168.11.0/24"
DEFAULT_USERNAME = "pi"
DEFAULT_PASSWORD = "ceticeti"

# get ALL gateway ips
def getLANips() -> [ipaddress.IPv4Address | ipaddress.IPv6Address]:
    gateways = netifaces.gateways()[netifaces.AF_INET]
    gateway_ips = []
    for gateway in gateways:
        gateway_ips.append(ipaddress.ip_address(gateway[0]))    

    return gateway_ips

# Scan the active LAN for servers with open ssh on port 22
def find_ssh_servers():
    result = []
    for gateway_ip in getLANips():
        netspec = findssh.netfromaddress(gateway_ip)
        coro = findssh.get_hosts(netspec, 22, "ssh", 1.0)
        sys.stdout = open(os.devnull, "w")
        lanhosts = asyncio.run(coro)
        sys.stdout = sys.__stdout__
        coro = findssh.get_hosts(ipaddress.IPv4Network(DEFAULT_USBGADGET_IPNETWORK), 22, "ssh", 1.0)
        sys.stdout = open(os.devnull, "w")
        usbhosts = asyncio.run(coro)
        sys.stdout = sys.__stdout__
        for ip in lanhosts+usbhosts:
            result.append(str(ip[0]))
    return result


# get hostnames for all ssh servers
def get_hostname_by_addr(addr):
    try:
        # Connect to the remote whale tag
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=addr,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD)
        _, stdout, _ = ssh.exec_command("hostname")
        hostname = stdout.readline().strip()
        ssh.close()
        return hostname
    except:
        return ""

# Verify we can connect to the remote system using ssh with default credentials
def can_connect(addr):
    try:
        # test connecting with ssh using default tag password
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=addr,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD)
        ssh.close()
    except BaseException:
        return False
    return True


# Perform local discovery of the tags and return the list of them
def tag_hostnames(hostnames):
    hnames = []
    for hname in hostnames:
        if re.match("wt-[a-z0-9]{6,}", hname):
            hnames.append(hname)
    return hnames


# Find all of the whale tags available on the local LAN
def list_whale_tags_online():
    servers = find_ssh_servers()
    hostnames = []
    for server in servers:
        hname = get_hostname_by_addr(server)
        if (hname):
            if (hname not in hostnames):
                hostnames.append(hname)
    tags = tag_hostnames(hostnames)
    return tags


# Prepare the list of files on the remote whale tag that are missing
# from the local data folder
def create_filelist_to_download(hostname):
    files_to_download = []
    try:
        # Connect to the remote whale tag
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD)

        # Prepare the local storage to accept the files
        local_data_folder = os.path.join(LOCAL_DATA_PATH, hostname)
        if not os.path.exists(local_data_folder):
            os.makedirs(local_data_folder)
        local_files = os.listdir(local_data_folder)

        # Check what files are available for download from the tag
        # Ignores any folders in tag
        remote_data_folder = os.path.normpath("/data")
        _, stdout, _ = ssh.exec_command("ls -p " + remote_data_folder + "| grep -v /")
        remote_files = stdout.readlines()

        # Create the list of files to download
        for fname in remote_files:
            fname = fname.strip()
            if (fname not in local_files):
                files_to_download.append(
                    os.path.join(remote_data_folder, fname))
                continue

            # Here: the file with this name is already present.
            # Compare its hash to the local file.
            # If different, lets re-download that file again.
            local_sha = sha256sum(os.path.join(local_data_folder, fname))
            _, stdout, _ = ssh.exec_command(
                "sha256sum " + os.path.join(remote_data_folder, fname))
            remote_sha = stdout.read().decode("utf-8").split(" ")[0]

            if (local_sha != remote_sha):
                files_to_download.append(
                    os.path.join(remote_data_folder, fname))

    finally:
        ssh.close()
    return files_to_download

#Stops data capture service on device
def stop_capture_service(hostname):
    if not can_connect(hostname):
        print("Could not connect to host: " + str(hostname))
        return
    print("Stopping data capture service on device " + hostname)
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD)
        ssh.exec_command("sudo systemctl stop ceti-tag-data-capture")
    finally:
        ssh.close()


# Download a file over sftp
def download_remote_file(hostname, remote_file):
    local_file = os.path.join(LOCAL_DATA_PATH, hostname)
    local_file = os.path.join(local_file, os.path.basename(remote_file))

    ssh = None
    sftp = None
    progress_bar = None

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD)
        sftp = ssh.open_sftp()

        # Get remote file size for progress bar
        remote_size = sftp.stat(remote_file).st_size

        # Create progress bar
        progress_bar = tqdm(
            desc=f"Downloading {os.path.basename(remote_file)}",
            total=remote_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            position=0,
            leave=True
        )

        # Callback to update progress bar
        def progress_callback(transferred, total):
            progress_bar.update(transferred - progress_bar.n)

        # Download with progress tracking
        sftp.get(remote_file, local_file, callback=progress_callback)

    finally:
        if progress_bar:
            progress_bar.close()
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()


def download_all(hostname):
    if not can_connect(hostname):
        print("Could not connect to host: " + str(hostname))
        return

    print("Connecting to " + hostname)
    stop_capture_service(hostname)

    # Get list of files to download
    filelist = create_filelist_to_download(hostname)
    filelist = [f for f in filelist if "lost+found" not in f]

    if not filelist:
        print("No new files to download")
        return

    # Calculate total size and count
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD)
        sftp = ssh.open_sftp()

        total_size = 0
        for filename in filelist:
            try:
                total_size += sftp.stat(filename).st_size
            except:
                pass

        sftp.close()
        ssh.close()

        # Print summary
        print(f"\nFound {len(filelist)} file(s) to download ({total_size / (1024**2):.2f} MB total)")
        print("-" * 60)

    except:
        print(f"\nFound {len(filelist)} file(s) to download")
        print("-" * 60)

    # Download files with progress bars
    start_time = time.time()
    for filename in filelist:
        download_remote_file(hostname, filename)

    # Print completion summary
    elapsed_time = time.time() - start_time
    print("-" * 60)
    print(f"Downloaded {len(filelist)} file(s) in {elapsed_time:.1f} seconds")
    print("Done")


# CAREFUL: ERASES ALL DATA FROM WHALE TAG
def clean_tag(hostname):
    if not can_connect(hostname):
        print("Could not connect to host: " + str(hostname))
        return

    stop_capture_service(hostname)

    # Check if all files have been downloaded
    filelist = create_filelist_to_download(hostname)
    if filelist:
        print("Not all data have been downloaded from this tag. Quitting...")
        return

    # List all files that will be deleted
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD)
        sftp = ssh.open_sftp()

        # Get list of all files in /data/
        remote_files = sftp.listdir_attr("/data")
        files_to_delete = [f for f in remote_files if f.filename not in [".", "..", "lost+found"]]

        if not files_to_delete:
            print("No files to delete on device " + hostname)
            sftp.close()
            ssh.close()
            return

        # Show what will be deleted
        print(f"\nFiles to be deleted from device {hostname}:")
        print("-" * 60)
        total_size = 0
        for file_attr in files_to_delete:
            size_mb = file_attr.st_size / (1024**2)
            total_size += file_attr.st_size
            print(f"  {file_attr.filename:40s}  {size_mb:>8.2f} MB")
        print("-" * 60)
        print(f"Total: {len(files_to_delete)} file(s), {total_size / (1024**2):.2f} MB")
        print()

        sftp.close()

        # Perform deletion
        print(f"Erasing all collected data from device {hostname}...")
        ssh.exec_command("sudo rm -rf " + os.path.join("/data/","*.*"))
        print("Data erased successfully")

    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        ssh.close()


def cli(args: Namespace):
    if args.list:
        tag_list = list_whale_tags_online()
        for tag in tag_list:
            print(tag)

    if args.tag:
        download_all(args.tag.strip())

    if args.all:
        print("Searching for whale tags on LAN")
        tag_list = list_whale_tags_online()
        print("Found: " + str(tag_list))
        for tag in tag_list:
            download_all(tag)

    if args.clean_tag:
        clean_tag(args.clean_tag.strip())

    if args.clean_all_tags:
        print("Searching for whale tags on LAN")
        tag_list = list_whale_tags_online()
        print("Found: " + str(tag_list))
        for tag in tag_list:
            clean_tag(tag)
