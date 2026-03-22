terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state in S3.
  # IMPORTANT: Create this bucket manually before running `terraform init`:
  #   aws s3 mb s3://storydiff-tf-state --region us-east-1
  backend "s3" {
    bucket = "storydiff-tf-state"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}
