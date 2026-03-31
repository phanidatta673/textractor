#!/bin/bash
set -e

# Decommissioning script for Textractor project

# 1. Clean up local build artifacts
echo "Cleaning up local build artifacts..."
find . -name "dist" -type d -exec rm -rf {} +
find . -name "__pycache__" -type d -exec rm -rf {} +
rm -rf terraform/*.zip

# 2. Terraform Destroy
echo "Starting Terraform Destroy to remove AWS and GitHub resources..."
cd terraform
if [ -f ".terraform/terraform.tfstate" ] || [ -f "terraform.tfstate" ]; then
    terraform destroy -auto-approve \
        -var="github_token=$GITHUB_TOKEN" \
        -var="sprites_token=$SPRITES_TOKEN" \
        -var="github_owner=$GITHUB_OWNER" \
        -var="github_repo=$GITHUB_REPO" \
        -var="region=$AWS_REGION"
else
    echo "No terraform state found. Skipping destroy."
fi

echo "Decommissioning complete."
