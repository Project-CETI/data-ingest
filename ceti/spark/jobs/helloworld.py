# This file contains a sample PySpark application
# to be run on CETI EMR cluster for test purposes.

from pyspark.sql import SparkSession


def helloworld():
    spark = SparkSession.builder.appName("HelloWorld").getOrCreate()
    nums = spark.sparkContext.parallelize(["Hello", "World"])
    print(nums.map(lambda x: x).collect())
    spark.stop()


if __name__ == "__main__":
    helloworld()
