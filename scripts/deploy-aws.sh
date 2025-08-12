#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting AWS deployment of Shopping App${NC}"

# Configuration
PROJECT_NAME=${PROJECT_NAME:-"shopping-app"}
AWS_REGION=${AWS_REGION:-"us-east-1"}
ECR_REPOSITORY=""
DOCKER_IMAGE_NAME="${PROJECT_NAME}-backend"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --ecr-repo)
      ECR_REPOSITORY="$2"
      shift 2
      ;;
    --project-name)
      PROJECT_NAME="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --ecr-repo REPO_URI    ECR repository URI for Docker image"
      echo "  --project-name NAME    Project name (default: shopping-app)"
      echo "  --region REGION        AWS region (default: us-east-1)"
      echo "  --help                 Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

# Check required tools
check_dependencies() {
    echo -e "${YELLOW}📋 Checking dependencies...${NC}"
    
    local missing_tools=()
    
    if ! command -v terraform &> /dev/null; then
        missing_tools+=("terraform")
    fi
    
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if ! command -v git &> /dev/null; then
        missing_tools+=("git")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required tools: ${missing_tools[*]}${NC}"
        echo -e "${YELLOW}💡 Please install the missing tools and try again${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}❌ AWS credentials not configured${NC}"
        echo -e "${YELLOW}💡 Run 'aws configure' to set up your AWS credentials${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All dependencies are installed${NC}"
}

# Create ECR repository if needed
create_ecr_repository() {
    if [ -z "$ECR_REPOSITORY" ]; then
        echo -e "${YELLOW}🐳 Creating ECR repository...${NC}"
        
        local repo_name="${PROJECT_NAME}-backend"
        
        # Create ECR repository
        aws ecr create-repository \
            --repository-name "$repo_name" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256 \
            2>/dev/null || true
        
        # Get the repository URI
        ECR_REPOSITORY=$(aws ecr describe-repositories \
            --repository-names "$repo_name" \
            --region "$AWS_REGION" \
            --query 'repositories[0].repositoryUri' \
            --output text)
        
        echo -e "${GREEN}✅ ECR repository created/found: $ECR_REPOSITORY${NC}"
    fi
}

# Build and push Docker image
build_and_push_docker() {
    echo -e "${YELLOW}🐳 Building and pushing Docker image...${NC}"
    
    cd shopping
    
    # Build Docker image
    docker build -t $DOCKER_IMAGE_NAME:latest .
    
    # Tag for ECR
    docker tag $DOCKER_IMAGE_NAME:latest $ECR_REPOSITORY:latest
    
    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY
    
    # Push to ECR
    docker push $ECR_REPOSITORY:latest
    
    echo -e "${GREEN}✅ Docker image pushed successfully${NC}"
    cd ..
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    echo -e "${YELLOW}🏗️ Deploying AWS infrastructure with Terraform...${NC}"
    
    cd terraform
    
    # Check if terraform.tfvars exists
    if [ ! -f "terraform.tfvars" ]; then
        echo -e "${RED}❌ terraform.tfvars file not found${NC}"
        echo -e "${YELLOW}💡 Please copy terraform.tfvars.example to terraform.tfvars and fill in your values${NC}"
        echo -e "${BLUE}Example:${NC}"
        echo "cp terraform.tfvars.example terraform.tfvars"
        echo "# Edit terraform.tfvars with your configuration"
        exit 1
    fi
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan \
        -var="backend_image=$ECR_REPOSITORY:latest" \
        -var="project_name=$PROJECT_NAME" \
        -var="aws_region=$AWS_REGION" \
        -out=tfplan
    
    # Apply deployment
    echo -e "${YELLOW}🚀 Applying Terraform configuration...${NC}"
    terraform apply tfplan
    
    echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
    cd ..
}

# Run database migrations
run_database_migrations() {
    echo -e "${YELLOW}🗃️ Running database migrations...${NC}"
    
    cd terraform
    
    local cluster_name=$(terraform output -raw ecs_cluster_name)
    local task_definition=$(terraform output -raw ecs_service_name | sed 's/-service/-backend/')
    local subnet_ids=$(terraform output -json private_subnet_ids | jq -r '.[] | @sh' | tr '\n' ',' | sed 's/,$//')
    local security_group=$(terraform output -raw ecs_cluster_name | sed 's/cluster/ecs-tasks-sg/')
    
    echo -e "${BLUE}Running Flask DB migrations...${NC}"
    
    # Run database initialization
    aws ecs run-task \
        --cluster "$cluster_name" \
        --task-definition "$task_definition" \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$subnet_ids],securityGroups=[sg-*],assignPublicIp=DISABLED}" \
        --overrides "{\"containerOverrides\":[{\"name\":\"${PROJECT_NAME}-backend\",\"command\":[\"flask\",\"db\",\"init\"]}]}" \
        --region "$AWS_REGION" || true
    
    # Run migrations
    aws ecs run-task \
        --cluster "$cluster_name" \
        --task-definition "$task_definition" \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$subnet_ids],securityGroups=[sg-*],assignPublicIp=DISABLED}" \
        --overrides "{\"containerOverrides\":[{\"name\":\"${PROJECT_NAME}-backend\",\"command\":[\"flask\",\"db\",\"migrate\",\"-m\",\"Initial migration\"]}]}" \
        --region "$AWS_REGION" || true
    
    # Apply migrations
    aws ecs run-task \
        --cluster "$cluster_name" \
        --task-definition "$task_definition" \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$subnet_ids],securityGroups=[sg-*],assignPublicIp=DISABLED}" \
        --overrides "{\"containerOverrides\":[{\"name\":\"${PROJECT_NAME}-backend\",\"command\":[\"flask\",\"db\",\"upgrade\"]}]}" \
        --region "$AWS_REGION"
    
    echo -e "${GREEN}✅ Database migrations completed${NC}"
    cd ..
}

# Seed initial data
seed_data() {
    echo -e "${YELLOW}🌱 Seeding initial data...${NC}"
    
    cd terraform
    local alb_url=$(terraform output -raw load_balancer_url)
    cd ..
    
    # Wait for service to be ready
    echo -e "${BLUE}Waiting for service to be ready...${NC}"
    sleep 30
    
    # Seed products
    if curl -f -X POST "$alb_url/admin/seed-products" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Products seeded successfully${NC}"
    else
        echo -e "${YELLOW}⚠️ Could not seed products automatically. You can do this later via:${NC}"
        echo -e "${BLUE}curl -X POST $alb_url/admin/seed-products${NC}"
    fi
}

# Main deployment function
main() {
    echo -e "${GREEN}Starting AWS deployment for: $PROJECT_NAME${NC}"
    echo -e "${BLUE}Region: $AWS_REGION${NC}"
    
    check_dependencies
    create_ecr_repository
    build_and_push_docker
    deploy_infrastructure
    run_database_migrations
    seed_data
    
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    
    # Show deployment info
    cd terraform
    echo -e "${YELLOW}📋 Deployment Information:${NC}"
    terraform output deployment_instructions
    cd ..
    
    echo -e "${GREEN}🚀 Your shopping app is now live!${NC}"
}

# Show help if no ECR repository is provided and we're not creating one
if [ -z "$ECR_REPOSITORY" ] && [ -z "$PROJECT_NAME" ]; then
    echo -e "${YELLOW}💡 Usage examples:${NC}"
    echo "  $0 --project-name my-shop --region us-west-2"
    echo "  $0 --ecr-repo 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-app"
    echo ""
    echo "Run $0 --help for more options"
    echo ""
fi

# Run main function
main "$@" 