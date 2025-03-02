variable "account_id" { sensitive = true }
variable "region" {}

variable "service_name" {}
variable "ecr_post_func_name" {}

variable "openai_api_key" { sensitive = true }
variable "x_bearer_token" { sensitive = true }
variable "x_api_key" { sensitive = true }
variable "x_api_key_secret" { sensitive = true }
variable "x_access_token" { sensitive = true }
variable "x_access_token_secret" { sensitive = true }
