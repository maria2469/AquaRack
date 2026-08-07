# AWS Services Deployment Guide for CockroachDB × AWS Hackathon

## AWS Services Used

This project actively uses the following AWS services for the hackathon:

### 1. Amazon S3 (Cold-Tier Storage)
- **Purpose**: Cold-tier memory archival for aged agent memories
- **Implementation**: Real S3 uploads via boto3 with local disk fallback
- **Configuration**: 
  - `S3_ENABLED=true` (default in config.py)
  - `S3_BUCKET=rackpulse-cold-storage` (configurable)
  - Automatic fallback to `./s3_lake/` when AWS credentials unavailable

### 2. AWS Lambda (Serverless Compute)
- **Purpose**: Scheduled background jobs for memory lifecycle management
- **Implementation**: Full Lambda handler in `app/lambda_handler.py`
- **Available Actions**:
  - `retier_memories` - Hot→Warm→Cold memory tiering
  - `generate_scheduled_report` - Daily CSV telemetry reports
  - `cleanup_old_telemetry` - 90-day data retention
  - `telemetry_snapshot` - Point-in-time snapshots
  - `resolve_episode_outcomes` - Episode outcome resolution
- **Deployment**: Ready for EventBridge scheduled triggers

### 3. Amazon CloudWatch (Monitoring)
- **Purpose**: Custom metrics publishing for operational monitoring
- **Implementation**: CloudWatch metrics publisher in `app/observability/cloudwatch_metrics.py`
- **Configuration**: `CLOUDWATCH_ENABLED=true` (default in config.py)
- **Metrics Tracked**:
  - GPUUtilisation, CoolingLoadKW, WaterSavedPct
  - AgentConfidence, WUEFactor, WaterLPerHr
  - Lambda execution metrics (duration, success, records processed)

## Configuration Setup

### Step 1: Create AWS S3 Bucket
```bash
aws s3 mb s3://rackpulse-cold-storage --region us-east-1
```

### Step 2: Configure Environment Variables
Copy `.env.aws.template` to `.env` and fill in your AWS credentials:

```bash
cp backend/.env.aws.template backend/.env
```

Update the `.env` file with your actual AWS credentials:
```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
S3_ENABLED=true
S3_BUCKET=rackpulse-cold-storage
CLOUDWATCH_ENABLED=true
```

### Step 3: Deploy AWS Lambda Function
```bash
# Create deployment package
cd backend
zip -r deployment.zip app/

# Create Lambda function
aws lambda create-function \
  --function-name rackpulse-lambda \
  --runtime python3.11 \
  --handler app.lambda_handler.handler \
  --zip-file fileb://deployment.zip \
  --role arn:aws:iam::your-account-id:role/LambdaExecutionRole \
  --region us-east-1

# Create EventBridge schedule for memory retiering
aws events put-rule \
  --name rackpulse-retier-schedule \
  --schedule-expression "rate(1 hour)" \
  --region us-east-1

# Add Lambda as target
aws events put-targets \
  --rule rackpulse-retier-schedule \
  --targets Id=1,Arn=arn:aws:lambda:us-east-1:your-account-id:function:rackpulse-lambda
```

### Step 4: Grant Lambda Permissions
```bash
# Grant S3 permissions
aws lambda add-permission \
  --function-name rackpulse-lambda \
  --statement-id s3-access \
  --action "lambda:InvokeFunction" \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:your-account-id:rule/rackpulse-retier-schedule
```

## Verification

### Test S3 Upload
```python
from app.lib.s3_client import upload_telemetry_snapshot_to_s3

test_data = {"device_id": "test", "timestamp": "2026-08-07T00:00:00Z", "cpu_pct": 50.0}
s3_uri = upload_telemetry_snapshot_to_s3(test_data)
print(f"Uploaded to: {s3_uri}")
```

### Test Lambda Handler Locally
```python
from app.lambda_handler import handler

test_event = {
    "source": "aws.events",
    "detail-type": "Scheduled Event",
    "detail": {"action": "retier_memories"}
}

result = handler(test_event)
print(f"Lambda result: {result}")
```

### Test CloudWatch Metrics
```python
from app.observability.cloudwatch_metrics import publish_telemetry_metrics

success = publish_telemetry_metrics(
    gpu_pct=75.0,
    cooling_load_kw=12.5,
    wue_factor=1.8,
    water_l_per_hr=45.2,
    agent_confidence=0.85
)
print(f"Metrics published: {success}")
```

## Production Deployment Checklist

- [ ] AWS S3 bucket created and configured
- [ ] AWS credentials configured in `.env` file
- [ ] Lambda function deployed to AWS
- [ ] EventBridge rules created for scheduled jobs
- [ ] IAM roles configured with proper permissions
- [ ] CloudWatch metrics publishing verified
- [ ] S3 cold-tier export tested successfully
- [ ] Lambda handler tested locally and in AWS
- [ ] Error handling and fallback mechanisms verified

## Fallback Behavior

The system gracefully falls back to local operations when AWS services are unavailable:

- **S3**: Falls back to `./s3_lake/` local directory
- **Lambda**: Can run locally as Python functions
- **CloudWatch**: Silently skips metric publishing when unavailable

This ensures the system remains functional for development and testing even without AWS credentials.