# This file contains a sample PySpark application
# to be run on CETI EMR cluster for test purposes.

import logging
from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

OUTPUT_BUCKET = "s3://ceti-data-test"

def helloworld():
    spark = SparkSession.builder.appName("HelloWorld").getOrCreate()
    rdd = spark.sparkContext.parallelize(["Hello", "World"])
    res = rdd.map(lambda x: x).collect()
    print(res)
    logger.info("%s", res)
    rdd.coalesce(1).saveAsTextFile(f"{OUTPUT_BUCKET}/HelloWorld.txt")
    spark.stop()

if __name__ == "__main__":
    helloworld()
