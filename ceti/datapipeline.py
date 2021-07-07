from argparse import Namespace
from pathlib import Path
import boto3
import os
import inspect

BUCKET_NAME = os.getenv("CETI_BUCKET") or 'ceti-data'
REGION_NAME = os.getenv("AWS_REGION") or 'us-east-1'


def datapipeline_run():
    # upload raw2processed.py to s3
    this_filename = inspect.getframeinfo(inspect.currentframe()).filename
    current_path = os.path.dirname(os.path.abspath(this_filename))
    s3_key = Path('pyspark') / str(current_path) / "raw2processed.py"
    s3client = boto3.client('s3')
    s3client.upload_file(local_path, BUCKET_NAME, s3_key)

    # Setup and run EMR cluster
    emr_client = boto3.client('emr', region_name=REGION_NAME)

    instances = {
        'MasterInstanceType': 'm5.xlarge',
        'SlaveInstanceType': 'm5.xlarge',
        'InstanceCount': 3,
        'KeepJobFlowAliveWhenNoSteps': False,
        'TerminationProtected': False,
    }

    steps = [{'Name': "raw2processed",
              'ActionOnFailure': 'CONTINUE',
              'HadoopJarStep': {
                  'Jar': 'command-runner.jar',
                  'Args': ['spark-submit', '--deploy-mode', 'cluster',
                           f's3://{BUCKET_NAME}/{s3_key}']
              }
              }]

    apps = [{'Name': 'Hadoop'},
            {'Name': 'Hive'},
            {'Name': 'Spark'}]

    response = client.run_job_flow(
        Name="raw2processed CETI data pipeline EMR cluster",
        ReleaseLabel='emr-5.30.1',
        Instances=instances,
        Steps=steps,
        Applications=apps
        VisibleToAllUsers=True,
        JobFlowRole='EMR_EC2_DefaultRole',
        ServiceRole='EMR_DefaultRole')
    print("cluster_id: " + response('JobFlowId'))


def cli(args: Namespace):
    if args.run:
        datapipeline_run()
