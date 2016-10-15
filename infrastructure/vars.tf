variable "aws_access_key" {}
variable "aws_secret_key" {}
variable "region" {
  description = "The region to apply these templates to (e.g. us-east-1)"
  default = "us-west-2"
}
variable "pushpin_image" {
  description = "The name of the Docker image to deploy for the Pushpin server"
  default = "fanout/pushpin"
}

variable "pushpin_version" {
  description = "The version (i.e. tag) of the Docker container to deploy for the Pushpin server"
  default = "latest"
}

variable "pushpin_external_port" {
  description = "The port the Pushpin Docker container listens on for external HTTP requests"
  default = 7999
}

variable "pushpin_control_port" {
  description = "The port the Pushpin Docker container listens on for control messages"
  default = 5561  
}

variable "backend_image" {
  description = "The name of the Docker image to deploy for the backend"
  default = "beaucronin/restream-backend"
}

variable "backend_version" {
  description = "The version (i.e. tag) of the Docker container to deploy for the backend"
  default = "latest"
}

variable "backend_port" {
  description = "The port the backend Docker container listens on for HTTP requests"
  default = 5000
}

variable "keypair_name" {
  description = "The name of the Key Pair that can be used to SSH to each EC2 instance in the ECS cluster"
}

variable "vpc_id" {
  description = "The id of the VPC where the ECS cluster should run"
}

# variable "elb_subnet_ids" {
#   description = "A comma-separated list of subnets where the ELBs should be deployed"
# }

variable "ecs_cluster_subnet_ids" {
  description = "A comma-separated list of subnets where the EC2 instances for the ECS cluster should be deployed"
}

variable "ami" {
  description = "The AMI for each EC2 instance in the cluster"
  # These are the ids for Amazon's ECS-Optimized Linux AMI from:
  # https://aws.amazon.com/marketplace/ordering?productId=4ce33fd9-63ff-4f35-8d3a-939b641f1931. Note that the very first
  # time, you have to accept the terms and conditions on that page or the EC2 instances will fail to launch!
  default = {
    us-east-1     = "ami-55870742"
    us-west-1     = "ami-07713767"
    eu-central-1  = "ami-3b54be54"
    eu-west-1     = "ami-c74127b4"
    us-west-2     = "ami-562cf236"
  }
}

variable "message_cache_table" {
  description = "The DynamoDB table that contains previous messages for each stream"
  default = "RestreamMessageCache"
}
