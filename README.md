# data-ingest

Source code for the data pipeline that starts with ingesting the data from the embedded data collection devices (whale tags, moorings, etc), uploads it to the cloud and combines in a unified dataset consumable by the machine learning pipelines for [project CETI](https://www.projectceti.org/).

## Installation from wheel file

The wheel file can be installed using `pip`. For example, if you have `ceti-1.0.0-py3-none-any.whl`:

```console
pip install ceti-1.0.0-py3-none-any.whl
```

## Installation from source

If you want to install from sources:

```console
git clone https://github.com/Project-CETI/data-ingest.git
cd data-ingest
pip install .
```

For developer mode use:

```console
pip install -e .
```

Additionally you can build a wheel file for binary distribution of the package. The wheel file will be located in the `./dist` folder.

```console
make build_tools && make build
```

## Usage

```console
$ ceti -h
usage: ceti [command] [options]

optional arguments:
  -h, --help  show this help message and exit

Available commands:

    upload    Uploads local whale data to AWS S3 cloud.
    whaletag  Discover whale tags on LAN and download data off them.
```

## whaletag

This script contains code necessary to pull the data from whale tags that is on the same LAN as the machine running the script.

See command line arguments:

```console
ceti whaletag -h
```

## Uploading data to S3

To upload the files from the data directory use the `s3upload` command:

```console
ceti s3upload path_to_data_dir
```
