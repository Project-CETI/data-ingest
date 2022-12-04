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

On certain versions of the tag hardware, the data from hydrophones is stored in raw format. Convert it before upload with the following script:
```console
#!/bin/bash
OUTDIR="../flac/${PWD##*/}"
mkdir -p "$OUTDIR"
for f in *.raw; do
  IFS='.' read -r -a split_filename <<< "$f"
  flac --channels=3 --bps=16 --sample-rate=96000 --sign=signed --endian=big --force-raw-format "$f" --force --output-name="$OUTDIR/${split_filename[0]}.flac" &
done
wait
echo "( ・◡・)つ━☆  All done"
```
