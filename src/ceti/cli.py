#!/usr/bin/python3

# This file implements the main CLI interface entry point for the
# ceti command line tool.

import sys
from ceti import whaletag

def print_help():
    print("usage: ceti [help] [ whaletag ] {args}")
    exit(1)

def main():
    allowed_cmds = ["whaletag"]

    if ( len(sys.argv) < 2):
        print_help()

    cmd = sys.argv[1]

    if (cmd not in allowed_cmds):
        print_help()

    if cmd == "whaletag":
        sys.argv = sys.argv[1:]
        return whaletag.main()

if __name__ == "__main__":
    main()
