resource "aws_instance" "customer_api" {
  ami           = "ami-0123456789abcdef0"
  instance_type = "t3.micro"
  tags = { Name = "customer-api-host" }
}
