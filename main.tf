# ----------------------------------------------------------
# IAM
# ----------------------------------------------------------
# Lambda
resource "aws_iam_role" "lambda_execution_role" {
  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Action    = "sts:AssumeRole"
          Effect    = "Allow"
          Sid       = ""
          Principal = { Service = "lambda.amazonaws.com" }
        }
      ]
    }
  )
}

resource "aws_iam_policy" "iam_policy_invoke_bedrock" {
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : ["bedrock:InvokeModel"],
        "Resource" : [
          "arn:aws:bedrock:${var.region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
          "arn:aws:bedrock:${var.region}::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "iam_policy_lambda" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.iam_policy_invoke_bedrock.arn
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ----------------------------------------------------------
# ECR
# ----------------------------------------------------------
resource "aws_ecr_repository" "ecr_pokemon_quiz" {
  name         = var.ecr_post_func_name
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ----------------------------------------------------------
# Docker
# ----------------------------------------------------------
resource "null_resource" "pokemon_quiz_container" {
  triggers = {
    file_content_sha1 = sha1(
      join("", [for f in fileset("docker", "**/*") : filesha1("${path.module}/docker/${f}")])
    )
  }

  provisioner "local-exec" {
    command = <<-EOT
# docker login
aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${var.account_id}.dkr.ecr.${var.region}.amazonaws.com
# docker build
docker build -t ${var.ecr_post_func_name} -f ./docker/Dockerfile ./docker
# image tagging
docker tag ${var.ecr_post_func_name}:latest ${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.ecr_post_func_name}:latest
# push
docker push ${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.ecr_post_func_name}:latest
docker rmi -f ${var.ecr_post_func_name}:latest ${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/${var.ecr_post_func_name}:latest
    EOT
  }
}

# ----------------------------------------------------------
# Lambda
# ----------------------------------------------------------
resource "aws_lambda_function" "lambda_for_post" {
  function_name = var.service_name
  image_uri     = "${aws_ecr_repository.ecr_pokemon_quiz.repository_url}:latest"
  package_type  = "Image"
  role          = aws_iam_role.lambda_execution_role.arn
  memory_size   = 256
  timeout       = 300

  environment {
    variables = {
      OPENAI_API_KEY        = var.openai_api_key
      X_BEARER_TOKEN        = var.x_bearer_token
      X_ACCESS_TOKEN        = var.x_access_token
      X_ACCESS_TOKEN_SECRET = var.x_access_token_secret
      X_API_KEY             = var.x_api_key
      X_API_KEY_SECRET      = var.x_api_key_secret
    }
  }

  depends_on = [
    null_resource.pokemon_quiz_container,
    aws_ecr_repository.ecr_pokemon_quiz
  ]

  lifecycle {
    replace_triggered_by = [
      aws_ecr_repository.ecr_pokemon_quiz.id
    ]
  }
}

# ----------------------------------------------------------
# EventBridge
# ----------------------------------------------------------
# EventBridge Rule
resource "aws_cloudwatch_event_rule" "hourly_rule" {
  name                = "hourly-lambda-trigger"
  description         = "Trigger Lambda function every hour"
  schedule_expression = "rate(8 hours)"
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.hourly_rule.name
  target_id = "TriggerLambda"
  arn       = aws_lambda_function.lambda_for_post.arn
}

# EventBridge に Lambda を呼び出す権限を付与
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_for_post.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly_rule.arn
}

# ----------------------------------------------------------
# CloudWatch Logs
# ----------------------------------------------------------
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.lambda_for_post.function_name}"
  retention_in_days = 7
}
