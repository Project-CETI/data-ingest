#!/bin/bash
# LocalStack initialization script
# This runs automatically when LocalStack container starts
# See: https://docs.localstack.cloud/references/init-hooks/

echo "Initializing LocalStack S3 buckets..."

# Create production bucket (used by ceti CLI tools)
awslocal s3 mb s3://ceti-data
echo "Created bucket: ceti-data"

# Create test bucket (used by pytest)
awslocal s3 mb s3://ceti-data-test
echo "Created bucket: ceti-data-test"

# Create dev bucket (used by datapipeline/EMR jobs)
awslocal s3 mb s3://ceti-dev
echo "Created bucket: ceti-dev"

echo "LocalStack initialization complete!"
