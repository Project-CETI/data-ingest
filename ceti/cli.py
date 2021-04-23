# This file implements the main CLI interface entry point for the
# ceti command line tool.
import argparse
from pathlib import Path

from ceti import s3upload, whaletag


def main():
    parser = argparse.ArgumentParser(usage='ceti [command] [options]')

    # Subcommands
    subparsers = parser.add_subparsers(title='Available commands', metavar='')
    s3upload_parser = subparsers.add_parser('s3upload', help='Uploads local whale data to AWS S3 cloud.')
    whaletag_parser = subparsers.add_parser('whaletag', help='Discover whale tags on LAN and download data off them.')

    # Set default callable for each subcommand
    s3upload_parser.set_defaults(func=s3upload.cli)
    whaletag_parser.set_defaults(func=whaletag.cli)
    parser.set_defaults(func=lambda x: parser.print_help())  # Print help if no args

    # Whaletag subcommand CLI
    whaletag_parser.add_argument(
        "-l",
        "--list",
        help="List available whale tags",
        action="store_true")
    whaletag_parser.add_argument(
        "-t",
        "--tag",
        help="Download data from specific tag (by hostname)")
    whaletag_parser.add_argument(
        "-a",
        "--all",
        help="Download all data from all whale tags",
        action="store_true")
    whaletag_parser.add_argument(
        "-ct",
        "--clean_tag",
        help="Removes all collected data from a whale tag (by hostname)")
    whaletag_parser.add_argument(
        "-ca",
        "--clean_all_tags",
        help="Removes all collected data from all accessible tags",
        action="store_true")

    # s3upload subcommand CLI
    s3upload_parser.add_argument(
        "-t",
        "--dry-run",
        help="List source and destination paths, but do not upload anything",
        action="store_true")

    s3upload_parser.add_argument(
        "-d",
        "--debug",
        help="Show debug messages during upload",
        action="store_true")

    s3upload_parser.add_argument(
        "data_directory",
        type=Path,
        help="Path to the data directory where all the files are stored")


    # Parse args and call whatever function was selected
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
