terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

provider "github" {
  token = var.github_token
  owner = var.github_owner
}

# S3 Bucket for Uploads
resource "aws_s3_bucket" "uploads" {
  bucket_prefix = "text-extractor-uploads-"
  force_destroy = true
}

resource "aws_s3_bucket_lifecycle_configuration" "uploads_lifecycle" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    id     = "delete-after-1-day"
    status = "Enabled"
    expiration {
      days = 1
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "uploads_cors" {
  bucket = aws_s3_bucket.uploads.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET"]
    allowed_origins = ["*"]
    max_age_seconds = 3000
  }
}

# DynamoDB Table for Status and Content
resource "aws_dynamodb_table" "extractions" {
  name         = "Extractions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "fileId"

  attribute {
    name = "fileId"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

# EC2 Security Group
resource "aws_security_group" "web_sg" {
  name        = "textractor-web-sg"
  description = "Allow HTTP and SSH traffic"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM Role for EC2
resource "aws_iam_role" "ec2_role" {
  name = "text_extractor_ec2_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "text_extractor_ec2_policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.uploads.arn,
          "${aws_s3_bucket.uploads.arn}/*"
        ]
      },
      {
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.extractions.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "text_extractor_ec2_profile"
  role = aws_iam_role.ec2_role.name
}

# Get Latest Ubuntu 22.04 AMI
data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

resource "aws_key_pair" "deployer" {
  key_name   = "textractor-deployer-key"
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDuSdLQJd6fEBdqb5+oX2/BzU4CxCbf8NITvtFxF4WUHhWqHUiXkhqQiN9YyptXZbiUvmb/yb2eCHra0+a3LptS4RVGpp869QMqK3qlTOO/Ua5+pgJuXiIdJrG43qxhaEhbP9Sd5CW9hTq2qZ4oFEtrDJfEgP2ElY+nkZA3WtQ/NMP2VR0oZrc11rHUx51Jl+NhQEu2T7JloPIEuyWL9bqV1vBb9ENo0U/8JtNAu+tEvqJ92asAO5IxzvilsWHJD2U/X7yBxDmzGceI6cvJmDeupkJR/kxdi3adaQvk5hTOYsNgrPxLOUXBknhyKFsfCERFXSjEm48UhSpJH5GsNz+RtLoUOm6cRg8fjn2N942175OT6tVSQLzh1/0xCVzDlOHilFAaKsO59JjWqifvvGXV6xX1HgqqliwzSjvlUfCGm3l/NCWU2VWRnQemHka0JdrJZlA1xp24U3B+tKXDFmY2Yfxxk7weDCCEjITzEZ8714tvvYiJuasYo/VgyvN8j+F2xAVEa0/Tp12rPHcwSGpUw0jTrNXc4z8eWZvWHXQBI3Mvb9mfd8zXjT0Yljd91X6kQUgBDizTB2KRWzckFfZcaMwIUoqPvCB7dWyj1qpy080AukVRJjx605OzcLEugXn6IAaoHjEx/SVb1o0vtTE7ONP39Rw360YiNIyYByKBhQ== phanidatta673.com"
}

# EC2 Instance
resource "aws_instance" "monolith" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t2.micro"
  key_name               = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.web_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  user_data = <<EOF
#!/bin/bash
# Force recreation comment: v1.1.2
exec > /home/ubuntu/userdata.log 2>&1
echo "Starting user_data execution..."

# Disable firewall for initial testing
ufw disable

# Set environment variables for the session and persistence
export SECRET_CODE=${var.secret_code}
export BUCKET_NAME=${aws_s3_bucket.uploads.id}
export TABLE_NAME=${aws_dynamodb_table.extractions.name}
export SPRITES_TOKEN=${var.sprites_token}
export GITHUB_TOKEN=${var.github_token}
export GITHUB_REPOSITORY="${var.github_owner}/${var.github_repo}"
export AWS_DEFAULT_REGION=${var.region}
export GEMINI_API_KEY=${var.gemini_api_key}
export GITHUB_WEBHOOK_SECRET=${var.github_webhook_secret}

echo "export SECRET_CODE=${var.secret_code}" >> /etc/profile
echo "export BUCKET_NAME=${aws_s3_bucket.uploads.id}" >> /etc/profile
echo "export TABLE_NAME=${aws_dynamodb_table.extractions.name}" >> /etc/profile
echo "export SPRITES_TOKEN=${var.sprites_token}" >> /etc/profile
echo "export GITHUB_TOKEN=${var.github_token}" >> /etc/profile
echo "export GITHUB_REPOSITORY=${var.github_owner}/${var.github_repo}" >> /etc/profile
echo "export AWS_DEFAULT_REGION=${var.region}" >> /etc/profile
echo "export GEMINI_API_KEY=${var.gemini_api_key}" >> /etc/profile
echo "export GITHUB_WEBHOOK_SECRET='${var.github_webhook_secret}'" >> /etc/profile

# Install system dependencies
apt-get update -y
apt-get install -y python3-pip git

# Clone the repository
echo "Cloning repository..."
cd /home/ubuntu
git clone -b feature/text-extraction-improvements https://${var.github_token}@github.com/${var.github_owner}/${var.github_repo}.git
cd ${var.github_repo}/backend/monolith

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install fastapi uvicorn boto3 pypdf python-docx python-multipart jinja2

# Create a systemd service for the FastAPI app
echo "Creating systemd service..."
cat <<EOT > /etc/systemd/system/textractor.service
[Unit]
Description=Textractor FastAPI Monolith
After=network.target

[Service]
User=root
WorkingDirectory=/home/ubuntu/${var.github_repo}/backend/monolith
Environment="SECRET_CODE=${var.secret_code}"
Environment="BUCKET_NAME=${aws_s3_bucket.uploads.id}"
Environment="TABLE_NAME=${aws_dynamodb_table.extractions.name}"
Environment="SPRITES_TOKEN=${var.sprites_token}"
Environment="GITHUB_TOKEN=${var.github_token}"
Environment="GITHUB_REPOSITORY=${var.github_owner}/${var.github_repo}"
Environment="AWS_DEFAULT_REGION=${var.region}"
Environment="GEMINI_API_KEY=${var.gemini_api_key}"
Environment="GITHUB_WEBHOOK_SECRET=${var.github_webhook_secret}"
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 80
Restart=always

[Install]
WantedBy=multi-user.target
EOT

# Start and enable the service
echo "Starting service..."
systemctl daemon-reload
systemctl enable textractor
systemctl start textractor

echo "user_data execution complete."
EOF

  user_data_replace_on_change = true

  tags = {
    Name = "TextExtractorMonolith"
  }
}
