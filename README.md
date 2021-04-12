# data-ingest

Source code for the data pipeline that starts with ingesting the data from the embedded data collection devices (whale tags, moorings, etc), uploads it to the cloud and combines in a unified dataset consumable by the machine learning pipelines for [project CETI](https://www.projectceti.org/).

## Uploading data to S3

To upload the files from the data directory run the `data_upload` script:

```bash
python -m data_upload path_to_data_dir
```
