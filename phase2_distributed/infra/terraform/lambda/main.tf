# Scheduled Lambda blueprint (SDD Section 4.1: "Lambda — Scheduled jobs:
# weather ingestion, report generation, memory pruning, alert
# notifications"; Section 12.2: memory re-tiering / CDC export).
# Illustrative only — see ../README.md before applying.

variable "aws_region" {
  default = "us-east-1"
}

resource "aws_iam_role" "lambda_exec" {
  name = "aquamind-lambda-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Package phase2_distributed/memory_tiering/retier_job.py (+ deps) into a
# .zip before applying — see ../README.md.
resource "aws_lambda_function" "memory_retier" {
  function_name = "aquamind-memory-retier"
  handler       = "retier_job.handler"
  runtime       = "python3.12"
  filename      = "retier_job.zip"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 300
  environment {
    variables = {
      DATABASE_URL      = "cockroachdb://<user>:<password>@<host>:26257/aquamind"
      AQUAMIND_S3_LAKE_DIR = "s3://aquamind-cold-tier"
    }
  }
}

resource "aws_cloudwatch_event_rule" "nightly_retier" {
  name                = "aquamind-nightly-memory-retier"
  schedule_expression = "rate(1 day)"
}

resource "aws_cloudwatch_event_target" "retier_target" {
  rule = aws_cloudwatch_event_rule.nightly_retier.name
  arn  = aws_lambda_function.memory_retier.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.memory_retier.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.nightly_retier.arn
}
