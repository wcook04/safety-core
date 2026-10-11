# The orders database. `terraform apply` here changes a live system.
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "region" {
  type    = string
  default = "eu-west-2"
}

provider "aws" {
  region = var.region
}

resource "aws_db_instance" "orders" {
  identifier          = "orders-db"
  engine              = "postgres"
  engine_version      = "16"
  instance_class      = "db.t4g.micro"
  allocated_storage   = 20
  username            = "orders"
  manage_master_user_password = true
  skip_final_snapshot = false
  deletion_protection = true
}
