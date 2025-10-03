# Testing Guide

This guide covers how to run tests for the CETI data ingestion tools, both locally and in CI/CD.

## Overview

The project uses **LocalStack** to emulate AWS S3 locally, allowing you to test without real AWS credentials.

## Quick Start

### Local Testing (Developers)

```bash
# One-time setup
docker pull localstack/localstack

# Run tests
make test-local
```

That's it! The `make test-local` command:
1. Starts LocalStack in Docker
2. Sets up test environment variables
3. Runs pytest
4. Stops LocalStack

### Manual Testing (Advanced)

```bash
# Create and activate virtual environment (first time only)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .[test]

# Start LocalStack
make localstack-up

# Load environment variables and run tests
set -a && source .env.localstack && set +a && pytest

# Or run specific tests
set -a && source .env.localstack && set +a && pytest tests/test_s3upload.py -v

# Stop LocalStack
make localstack-down

# Clean LocalStack data
make localstack-clean
```

## Testing Against Real AWS (Optional)

If you have AWS credentials configured, you can run tests against real AWS S3:

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests WITHOUT LocalStack environment variables
pytest

# Tests will use your AWS credentials from ~/.aws/credentials
# and connect to real AWS S3
```

**Important:** Make sure `AWS_ENDPOINT_URL` is NOT set:
```bash
# Check if variable is set
echo $AWS_ENDPOINT_URL

# Unset if needed
unset AWS_ENDPOINT_URL

# Or start a fresh shell
exit  # then reopen terminal
```

## Production Workflow (Unchanged)

Field researchers continue using real AWS as before:

```bash
# Configure AWS credentials (one-time setup)
aws configure

# Authenticate to CodeArtifact
make login

# Use CLI tools as normal
ceti whaletag -a
ceti s3upload ./data
```

**No changes required!** The code automatically uses real AWS when `AWS_ENDPOINT_URL` is not set.

## Environment Variables

### Local Testing (LocalStack)

Set in `.env.localstack`:

```bash
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=cetitest
AWS_SECRET_ACCESS_KEY=cetitest
AWS_REGION=us-east-1
CETI_BUCKET=ceti-data-test
```

### Production

Uses standard AWS credential chain (no `.env` file needed):
1. `~/.aws/credentials` (from `aws configure`)
2. Environment variables (if set)
3. IAM roles (on EC2/ECS)

## Test Structure

### Unit Tests

Located in `tests/test_s3upload.py`:
- File discovery (`test_get_filelist`)
- S3 upload logic (`test_file_upload`)

### Integration Tests

Located in `tests/test_integration_*.py`:
- Hash-based deduplication
- End-to-end upload workflows
- Device ID validation
- Epoch timestamp renaming

### Test Fixtures

Defined in `tests/conftest.py`:
- `s3_client` - Boto3 S3 client (LocalStack or real AWS)
- `test_bucket` - Test bucket with automatic creation/cleanup
- Session-scoped fixtures for performance

## Running Specific Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_s3upload.py

# Run specific test function
pytest tests/test_s3upload.py::test_get_filelist

# Run with verbose output
pytest -v

# Run with output capture disabled
pytest -s
```

## LocalStack Limitations

LocalStack Free Tier supports S3 and other basic AWS services, which is sufficient for testing the data ingestion tools.

**Supported with LocalStack:**
- ✅ `ceti s3upload` - S3 upload with deduplication
- ✅ `ceti general_offload` - File offloading and S3 upload
- ✅ All pytest tests (S3-based)

**Not supported (requires real AWS or LocalStack Pro):**
- ❌ `ceti datapipeline` - Requires EMR (Elastic MapReduce)
- ❌ EMR cluster operations

If you try to run `ceti datapipeline` with LocalStack, you'll see:
```
ClientError: The API for service 'emr' is either not included in your current
license plan or has not yet been emulated by LocalStack.
```

**Solution:** Use real AWS credentials (not LocalStack) to test EMR/datapipeline functionality.

## Troubleshooting

### LocalStack not starting

```bash
# Check if LocalStack is running
docker ps | grep localstack

# Check logs
docker-compose -f docker-compose.localstack.yml logs

# Restart LocalStack
make localstack-down
make localstack-up
```

### Tests failing with connection errors

```bash
# Ensure LocalStack is accessible
curl http://localhost:4566/_localstack/health

# Check AWS_ENDPOINT_URL is set
echo $AWS_ENDPOINT_URL
```

### Port 4566 already in use

```bash
# Find process using port 4566
lsof -i :4566

# Stop existing LocalStack
make localstack-down
```

## Writing New Tests

When adding new tests that interact with S3:

```python
def test_my_feature(s3_client, test_bucket):
    """Test description"""
    # Use s3_client fixture (automatically points to LocalStack)
    s3_client.put_object(
        Bucket=test_bucket,
        Key='test-key',
        Body=b'test-data'
    )

    # Your test logic here
    result = my_function(s3_client, test_bucket)

    assert result == expected
```

The fixtures handle:
- Creating S3 client with correct endpoint
- Creating test bucket
- Cleaning up after tests

## Additional Resources

- [LocalStack Documentation](https://docs.localstack.cloud/)
- [pytest Documentation](https://docs.pytest.org/)
- [boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
