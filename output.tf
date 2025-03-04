output "lambda_function_name" {
  description = "The name of the Lambda function"
  value       = aws_lambda_function.lambda_for_post.function_name
}
