#!/usr/bin/python3

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

import asyncio
import findssh
import os
import paramiko
import re
import socket
import sys

def find_ssh_servers():
    netspec = findssh.netfromaddress(findssh.getLANip())
    coro = findssh.get_hosts(netspec, 22, "ssh", 1.0)
    sys.stdout = open(os.devnull, "w")
    hosts = asyncio.run(coro)
    sys.stdout = sys.__stdout__
    return hosts

def get_hostnames_by_addr(addrs):
    hostnames = []
    for a in addrs:
        addr = str(a[0])
        hname = socket.gethostbyaddr(addr)[0]
        hname = hname.split(".")[0]
        hostnames.append(hname)
    return hostnames

# Perform local discovery of the tags and return the list of them
def tag_hostnames(hostnames):
    hnames = []
    for hname in hostnames:
        if re.match("wt-[a-z0-9]{12}",hname):
            try:
                # test connecting with ssh using default tag password
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hname,username="pi", password="ceticeti")
                ssh.close()
                hnames.append(hname)
            except:
                continue
    return hnames



def list_whale_tags_online():
    servers = find_ssh_servers()
    hostnames = get_hostnames_by_addr(servers)
    tags = tag_hostnames(hostnames)
    return tags

def main():
    tags = list_whale_tags_online()
    print(tags)

if __name__ == "__main__":
    main()
