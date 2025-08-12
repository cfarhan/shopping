#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="shopping-app"
AWS_REGION="us-east-1"
DOCKER_IMAGE_NAME="shopping-app-backend"

echo -e "${GREEN}🚀 Starting deployment of Shopping App${NC}"

# Check required tools
check_dependencies() {
    echo -e "${YELLOW}📋 Checking dependencies...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is required but not installed${NC}"
        exit 1
    fi
    
    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}❌ Terraform is required but not installed${NC}"
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI is required but not installed${NC}"
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}❌ npm is required but not installed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All dependencies are installed${NC}"
}

# Build Docker image
build_backend() {
    echo -e "${YELLOW}🐳 Building backend Docker image...${NC}"
    
    cd shopping
    docker build -t $DOCKER_IMAGE_NAME:latest .
    
    # Tag for ECR (if using ECR)
    # ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    # ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$DOCKER_IMAGE_NAME"
    # docker tag $DOCKER_IMAGE_NAME:latest $ECR_URI:latest
    
    echo -e "${GREEN}✅ Backend Docker image built successfully${NC}"
    cd ..
}

# Build frontend
build_frontend() {
    echo -e "${YELLOW}⚛️ Building React frontend...${NC}"
    
    cd shopping/frontend
    npm install
    npm run build
    
    echo -e "${GREEN}✅ Frontend built successfully${NC}"
    cd ../..
}

# Deploy infrastructure
deploy_infrastructure() {
    echo -e "${YELLOW}🏗️ Deploying AWS infrastructure with Terraform...${NC}"
    
    cd terraform
    
    # Check if terraform.tfvars exists
    if [ ! -f "terraform.tfvars" ]; then
        echo -e "${RED}❌ terraform.tfvars file not found${NC}"
        echo -e "${YELLOW}💡 Please copy terraform.tfvars.example to terraform.tfvars and fill in your values${NC}"
        exit 1
    fi
    
    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan
    
    echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
    cd ..
}

# Deploy frontend to S3
deploy_frontend() {
    echo -e "${YELLOW}📤 Deploying frontend to S3...${NC}"
    
    cd terraform
    BUCKET_NAME=$(terraform output -raw frontend_bucket_name)
    cd ..
    
    aws s3 sync shopping/frontend/build/ s3://$BUCKET_NAME --delete
    
    # Invalidate CloudFront cache
    DISTRIBUTION_ID=$(cd terraform && terraform output -raw cloudfront_domain_name | cut -d'.' -f1)
    aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"
    
    echo -e "${GREEN}✅ Frontend deployed to S3 and CloudFront cache invalidated${NC}"
}

# Main deployment function
main() {
    echo -e "${GREEN}Starting deployment process...${NC}"
    
    check_dependencies
    build_backend
    build_frontend
    deploy_infrastructure
    deploy_frontend
    
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    
    # Show outputs
    cd terraform
    echo -e "${YELLOW}📋 Deployment Information:${NC}"
    terraform output deployment_instructions
    
    echo -e "${GREEN}Frontend URL:${NC} $(terraform output -raw cloudfront_url)"
    echo -e "${GREEN}Backend API URL:${NC} $(terraform output -raw load_balancer_url)"
}

# Run main function
main "$@" 