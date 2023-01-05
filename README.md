# data-ingest

Source code for the CLI tool that ingests the data from the embedded data collection devices (whale tags, moorings, etc) and uploads it to the AWS cloud (S3) to later be combined in a unified dataset consumable by the machine learning pipelines in ApacheSpark for [project CETI](https://www.projectceti.org/).
The code targets Linux machines, although we attempted to use OS agnostic libraries where possible to ease porting of this code if need be.

There are a few assumptions made in this code.

#### For whale tags

1) It is assumed that a whale tag will be present on the same LAN, have ssh server running on port 22, and have a hostname of type wt-AABBCCDDEEFF.

2) It is assumed that the hostname is universally unique and constant.

3) The [embedded software](https://github.com/Project-CETI/whale-tag-embedded/tree/main/packages/ceti-tag-set-hostname) for the whale tags actually sets the hostname that way.

4) Whale tags are mechanically isolated to withstand high pressures, so we assume LAN is a WiFi.

#### For moorings

..and other potential sources of data attached as external storage to the machine that is uploading the data to S3.

1) It is assumed that the data folder contains subfolders that correspond to unique device IDs. For example, a mooring would have its data in a mg-AABBCCDDEEFF subfolder.

2) It is assumed that those subfolders are universally unique and constant.

## Installation

First make sure you have [AWS Credentials properly set](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) to access AWS infrastructure. After that execute:

```console
make login
pip install ceti
```

### Installation from wheel file

The wheel file can be installed using `pip`. For example, if you have `ceti-1.0.0-py3-none-any.whl`:

```console
pip install ceti-1.0.0-py3-none-any.whl
```

### Installation from source

If you want to install from sources:

```console
git clone https://github.com/Project-CETI/data-ingest.git
cd data-ingest
pip install .
```

## Usage

```console
$ ceti -h
usage: ceti [command] [options]

optional arguments:
  -h, --help  show this help message and exit

Available commands:

    s3upload  Uploads local whale data to AWS S3 cloud.
    whaletag  Discover whale tags on LAN and download data off them.
```

## whaletag

This script contains code necessary to pull the data from whale tags that is on the same LAN as the machine running the script.

See command line arguments:

```console
ceti whaletag -h
```

A typical use case would have a WiFi network with a Linux machine connected to it, and a whale tag's onboard embedded computer also connected to the same WiFi.
Then one could:

Download all data from all whaletags present on the LAN

```console
ceti whaletag -a
```

Clean all whaletags. Caution - this is dangerous. It removes all data from the tags. Only do this after you successfully uploaded the data to S3.

```console
ceti whaletag -ca
```

Find all whaletags on the LAN

```console
ceti whaletag -l
```

Download data from one specific whaletag

```console
ceti whaletag -t wr-AABBCCEEDDFF
```

Delete data from the whaletag

```console
ceti whaletag -ct wr-AABBCCEEDDFF
```



## Offloading/Uploading Generic Non-Tag Data
The `general_offload.sh` script will handle all the offloading and uploading for non-tag data. Simply pass the file path to the data, and the ID of the device that captured the data.

If the data was captured on a shared ceti device like a drone or gopro, there should be a device ID label on the device. The ID that is given will be checked against a list of registered devices kept in s3: https://s3.console.aws.amazon.com/s3/object/ceti-data?region=us-east-1&prefix=Device+ID+List.txt
If your device is not listed here, you can register it with a unique ID.

`general_offload.sh` will create a temporary staging folder to offload the files to. It will also save backup copies of the files in `data/backup`. Once it offloads all the files onto the local mahcine, it will upload them all to s3, then delete the temporary folder.

Example from `data_ingest` directory. **This is the recommended way to offload and upload data** 
```console
source general_offload.sh /media/mangohouse/3531-3034/DCIM/100MEDIA/ CETI-DJI_MINI2-1
```

The `general_offload.sh` script uses other `ceti` tools named `general_offload` and `s3upload`. It just calls them in succession. If you would like to use the `general_offload` tool manually, you can do so, but will need to provide an additional path to the temporary folder to be used.

To get a list of supported commands:

```console
ceti general_offload -h
```

To preview a list of files to be offloaded:

```console
ceti general_offload -t <path_to_files> <device_id> <temporary_folder>
```

To perform actual data offload:

```console
ceti general_offload <path_to_files> <device_id> <temporary_folder>
```

**Note that when you use the `general_offload` tool manually, you are responsible for manually deleting the temporary folder.**

## Uploading data to S3

To upload the files from the data directory use the `s3upload` command. It establishes connection to the S3 bucket for raw data and attempts to upload all the data from the folder you specify.
This command also attempts to deduplicate the data during upload in order to provide upload resume capability. However, if your upload takes longer than 24 hours, and the connection breaks, some files might still be reuploaded.
We aired on the side of caution and decided it is better to sometimes upload more than needed and dedup the data later, than potentially loose precious data.

To get a list of supported commands:

```console
ceti s3upload -h
```

To preview a list of files and locations for the upload, assuming your data is in ./data:

```console
ceti s3upload -t ./data
```

To perform actual upload to S3:

```console
ceti s3upload ./data
```

## Development

### Building the package locally

For developer mode use from the project directory:

```console
pip install -e .
```

You can build a wheel file for binary distribution of the package. The wheel file will be located in the `./dist` folder.

```console
make build_tools && make build
```

### Releasing a new version

This package follows [semantic versioning](https://semver.org/) approach and [PEP440](https://www.python.org/dev/peps/pep-0440). In order to release a new version run the following steps:

```console
git checkout main && git pull
make release
```

This will autmatically bump the version at the patch level, e.g. `1.0.1` -> `1.0.2` and execute `git push origin main --tags`. After that the CI will run all the tests and publish the new version to  AWS CodeArtifact repo.

You can control the version level to bump using the `BUMP_LEVEL` environment variable.
Possible options are `major`, `minor`, `patch` (the default). For example:

```console
BUMP_LEVEL=minor make release
```

### Whale tag deployment

On certain versions of the tag hardware, the data from hydrophones is stored in raw format. Convert it before upload with the script scripts/flacencode.sh
There's also a convemnience script scripts/tag.sh that does the following automatically:
1) discover all tags on subnet
2) create a temporary folder for data offload
3) download all data from all tags into temporary folder
4) flac encode all audio, gzip all sensor csv data
5) copy the back-up of compressed data to /data-backup folder
6) upload all downloaded and compressed data to s3
7) clean all tags
