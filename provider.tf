terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }

    null = {
      source = "hashicorp/null"
    }
  }
}

provider "aws" {
  region = var.region
}
