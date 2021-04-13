# data-ingest

Source code for the data pipeline that starts with ingesting the data from the embedded data collection devices (whale tags, moorings, etc), uploads it to the cloud and combines in a unified dataset consumable by the machine learning pipelines for [project CETI](https://www.projectceti.org/).

## Installation

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

## Usage

```console
ceti -h
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
