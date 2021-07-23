# This file contains the actual PySpark code
# that is scheduled to be executed on a AWS EMR
# cluster that is configured and launched from
# the CETI CLI tool.
#
# This file is uploaded to the CETI S3 bucket
# each time this job runs. The work that this
# script does aims to process the raw data collected
# in the field and present in the /raw/ folder
# of the S3 CETI bucket into the processed format
# that is ready to be consumed by the
# ML training workloads

from pyspark.sql import SparkSession

if __name__ == "__main__":
    spark = SparkSession.builder.appName("CETI").getOrCreate()
    # Do useful things here
    spark.stop()
