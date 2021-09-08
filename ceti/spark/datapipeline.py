from argparse import Namespace
from importlib_resources import files
import os

import boto3

from ceti.spark.jobs import SparkJobs
from ceti.spark.utils import generate_bootstrap_script, get_s3_emr_dir, upload_files


# EMR Cluster configuration
REGION_NAME = os.getenv("AWS_REGION") or 'us-east-1'
EMR_VERSION = 'emr-6.3.0'
NUM_WORKERS = 3
WORKER_INSTANCE_TYPE = 'm5.xlarge'
DRIVER_INSTANCE_TYPE = 'm5.xlarge'


def _create_emr_cluster(job_name: str, job_s3_path: str, bootstrap_s3_path: str) -> str:
    """Setup and run EMR cluster in AWS"""

    emr_client = boto3.client('emr', region_name=REGION_NAME)

    instances = {
        'MasterInstanceType': DRIVER_INSTANCE_TYPE,
        'SlaveInstanceType': WORKER_INSTANCE_TYPE,
        'InstanceCount': NUM_WORKERS,
        'KeepJobFlowAliveWhenNoSteps': False,
        'TerminationProtected': False,
    }

    steps = [
        {
            'Name': 'setup Hadoop debugging',
            'ActionOnFailure': 'TERMINATE_CLUSTER',
            'HadoopJarStep': {
                'Jar': 'command-runner.jar',
                'Args': ['state-pusher-script']
            }
        },
        {
            'Name': job_name,
            'ActionOnFailure': 'TERMINATE_CLUSTER',
            'HadoopJarStep': {
                'Jar': 'command-runner.jar',
                'Args': [
                    'spark-submit',
                    '--deploy-mode', 'cluster',
                    job_s3_path,
                ]
            }
        }
    ]
    bootstrap_actions = [
        {
            'Name': 'Setup dependencies',
            'ScriptBootstrapAction': {
                'Path': bootstrap_s3_path,
            }
        },
    ]

    apps = [
        {'Name': 'Hadoop'},
        {'Name': 'Hive'},
        {'Name': 'Spark'}
    ]

    response = emr_client.run_job_flow(
        Name=f"CETI EMR cluster {job_name} job",
        ReleaseLabel=EMR_VERSION,
        LogUri=f"s3://{get_s3_emr_dir(job_name) / 'logs'}",
        Instances=instances,
        Steps=steps,
        Applications=apps,
        BootstrapActions=bootstrap_actions,
        VisibleToAllUsers=True,
        JobFlowRole='EMR_EC2_DefaultRole',
        ServiceRole='EMR_DefaultRole')

    return response['JobFlowId']


def submit_job(job: SparkJobs):
    """Start EMR cluster and submit arbitrary Spark job files into it"""

    bootstrap_script_local_path = generate_bootstrap_script()
    bootstrap_script_s3_path = f"s3://{get_s3_emr_dir(job.name) / 'bootstrap.sh'}"
    job_script_local_path = str(files('ceti.spark.jobs') / job.value)
    job_script_s3_path = f"s3://{get_s3_emr_dir(job.name) / job.value}"

    files_to_upload = [
        (
            # Job script
            job_script_local_path,
            job_script_s3_path
        ),
        (
            # Bootstrap script
            bootstrap_script_local_path,
            bootstrap_script_s3_path
        )
    ]

    upload_files(files_to_upload)
    return _create_emr_cluster(job.name, job_script_s3_path, bootstrap_script_s3_path)


def cli(args: Namespace):
    job = SparkJobs[args.job_name]
    job_id = submit_job(job)

    print(f"Started EMR cluster_id: {job_id}")
