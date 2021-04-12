# data-ingest

Source code for the data pipeline that starts with ingesting the data from the embedded data collection devices (whale tags, moorings, etc), uploads it to the cloud and combines in a unified dataset consumable by the machine learning pipelines for [project CETI](https://www.projectceti.org/).

# building

```
pip3 install --upgrade build
python3 -m build
```

# installing
```
cd dist
pip3 install ceti-*.tar.gz
```

# using
```
ceti help
```

# whaletag

This script contains code necessary to pull the data from whale tags that is on the same LAN as the machine running the script.


See command line arguments:

```
ceti whaletag -h
```

