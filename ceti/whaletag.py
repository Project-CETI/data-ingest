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

import findssh
import paramiko

from ceti.utils import sha256sum


LOCAL_DATA_PATH = os.path.join(os.getcwd(), "data")
DEFAULT_USBGADGET_IPNETWORK = "192.168.11.0/24"
DEFAULT_USERNAME = "pi"
DEFAULT_PASSWORD = "ceticeti"


# Scan the active LAN for servers with open ssh on port 22
def find_ssh_servers():
    netspec = findssh.netfromaddress(findssh.getLANip())
    coro = findssh.get_hosts(netspec, 22, "ssh", 1.0)
    sys.stdout = open(os.devnull, "w")
    lanhosts = asyncio.run(coro)
    sys.stdout = sys.__stdout__
    coro = findssh.get_hosts(ipaddress.IPv4Network(DEFAULT_USBGADGET_IPNETWORK), 22, "ssh", 1.0)
    sys.stdout = open(os.devnull, "w")
    usbhosts = asyncio.run(coro)
    sys.stdout = sys.__stdout__
    result = []
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
        remote_data_folder = os.path.normpath("/data")
        _, stdout, _ = ssh.exec_command("ls " + remote_data_folder)
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


# Download a file over sftp
def download_remote_file(hostname, remote_file):
    local_file = os.path.join(LOCAL_DATA_PATH, hostname)
    local_file = os.path.join(local_file, os.path.basename(remote_file))
    try:
        print("Downloading " + remote_file)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD)
        sftp = ssh.open_sftp()
        sftp.get(remote_file, local_file)
    finally:
        sftp.close()
        ssh.close()


def download_all(hostname):
    if not can_connect(hostname):
        print("Could not connect to host: " + str(hostname))
        return
    print("Connecting to " + hostname)
    filelist = create_filelist_to_download(hostname)
    for filename in filelist:
        if "lost+found" in filename:
            continue
        download_remote_file(hostname, filename)
    print("Done downloading")


# CAREFUL: ERASES ALL DATA FROM WHALE TAG
def clean_tag(hostname):
    if not can_connect(hostname):
        print("Could not connect to host: " + str(hostname))
        return
    filelist = create_filelist_to_download(hostname)
    if filelist:
        print("Not all data have been downloaded from this tag. Quitting...")
        return
    print("Erasing all collected data from whale tag " + hostname)
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname,
            username=DEFAULT_USERNAME,
            password=DEFAULT_PASSWORD)
        ssh.exec_command("rm -rf " + os.path.join("/data/","*"))
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
