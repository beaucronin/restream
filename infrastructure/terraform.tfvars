aws_access_key = "AKIAIDFZSJ4IRAVT5UIA"
aws_secret_key = "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"
account_id = "065558532272"

keypair_name = "bdc2014"

# Specify the VPC to use here. If you're not using custom VPCs and custom subnets, then:
#
# 1. Set vpc_id to the id of the "Default" VPC from the VPC list: https://console.aws.amazon.com/vpc/home?region=us-east-1#vpcs:
#    (e.g. vpc_id = "vpc-123456")
# 2. Set both subnet_ids lists to the subnet ids (separated with commas) from the subnet list: https://console.aws.amazon.com/vpc/home?region=us-east-1#subnets:
#    (e.g. elb_subnet_ids = "subnet-123456,subnet-4dkd3414,subnet-344kk3k1")
vpc_id = "vpc-f5353c90"
# elb_subnet_ids = ""
ecs_cluster_subnet_ids = "subnet-52625225,subnet-52625225,subnet-c5f3bd9c"
