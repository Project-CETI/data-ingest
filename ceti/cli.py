# This file implements the main CLI interface entry point for the
# ceti command line tool.
import argparse
from pathlib import Path

from ceti import s3upload, whaletag, general_offload

from ceti.spark import datapipeline
from ceti.spark.jobs import SparkJobs


def main():
    parser = argparse.ArgumentParser(usage='ceti [command] [options]')

    # Subcommands
    subparsers = parser.add_subparsers(title='Available commands', metavar='')
    s3upload_parser = subparsers.add_parser(
        's3upload', help='Uploads local whale data to AWS S3 cloud.')
    whaletag_parser = subparsers.add_parser(
        'whaletag', help='Discover whale tags on LAN and download data off them.')
    datapipeline_parser = subparsers.add_parser(
        'datapipeline', help='Launch the processing of the raw data uploaded from CETI sensors to S3 to processed format using AWS EMR cluster.')  # noqa
    general_offload_parser = subparsers.add_parser(
        'general_offload', help='Offloads generic data from storage device into \'data\' folder. Renames files to epoch time of file creation.')


    # Set default callable for each subcommand
    s3upload_parser.set_defaults(func=s3upload.cli)
    whaletag_parser.set_defaults(func=whaletag.cli)
    datapipeline_parser.set_defaults(func=datapipeline.cli)
    general_offload_parser.set_defaults(func=general_offload.cli)
    parser.set_defaults(func=lambda x: parser.print_help()
                        )  # Print help if no args

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

    # datapipeline subcommand CLI
    datapipeline_parser.add_argument(
        "job_name",
        choices=SparkJobs.names(),
        help="Launch specific spark job on EMR cluster")

    general_offload_parser.add_argument(
        "-o",
        "--offload",
        help="Offload files from storage device")

    general_offload_parser.add_argument(
        "-t",
        "--dry-run",
        help="List files found in data directory",
        action="store_true")

    general_offload_parser.add_argument(
        "data_dir",
        type=Path,
        help="Path to directory on storage device where files are stored. Path can be relative or absolute")

    general_offload_parser.add_argument(
        "id",
        type=str,
        help="The ID of the data capture device. This will be checked against the registered IDs in aws. If you are offloading from a shared ceti device, look for a device ID label on the device")

    general_offload_parser.add_argument(
        "temp_dir",
        type=str,
        help="The temporary directory to stage the files in before uploading to s3"
    )

    # Parse args and call whatever function was selected
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
