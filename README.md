# data-ingest
Source code for the data pipeline that starts with ingesting the data from the embedded data collection devices (whale tags, moorings, etc), uploads it to the cloud and combines in a unified dataset consumable by the machine learning pipelines for [project CETI](https://www.projectceti.org/).

# data-ingest-whale-tag.py

This script contains code necessary to pull the data from whale tags that is on the same LAN as the machine running the script.

Install requirements:
```
pip3 install -r requirements.txt
```

See command line arguments:

```
python3 data-ingest-whale-tag.py -h
```