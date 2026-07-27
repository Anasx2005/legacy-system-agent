resource "aws_instance" "customer_portal" {
  ami           = "ami-example"
  instance_type = "t3.medium"
}

resource "aws_s3_bucket" "portal_artifacts" {
  bucket = "customer-portal-artifacts"
}