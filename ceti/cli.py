# This file implements the main CLI interface entry point for the
# ceti command line tool.
import argparse

from ceti import upload, whaletag


def main():
    parser = argparse.ArgumentParser(usage='ceti [command] [options]')

    # Subcommands
    subparsers = parser.add_subparsers(title='Available commands', metavar='')
    upload_parser = subparsers.add_parser('upload', help='Uploads local whale data to AWS S3 cloud.')
    whaletag_parser = subparsers.add_parser('whaletag', help='Discover whale tags on LAN and download data off them.')

    # Set default callable for each subcommand
    upload_parser.set_defaults(func=upload.cli)
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

    # Parse args and call whatever function was selected
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
