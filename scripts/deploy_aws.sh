#!/usr/bin/env bash
set -euo pipefail

# Deploy Clinical Conversation Coach to AWS App Runner from ECR.
# Prerequisites: AWS CLI configured, Docker installed.

REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME="clinical-conversation-coach"
IMAGE_TAG="latest"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "=== Building Docker image ==="
docker build -t "$REPO_NAME" .

echo "=== Creating ECR repository (if needed) ==="
aws ecr describe-repository --repository-name "$REPO_NAME" 2>/dev/null || \
  aws ecr create-repository --repository-name "$REPO_NAME" --region "$REGION"

echo "=== Authenticating Docker to ECR ==="
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URI"

echo "=== Tagging and pushing image ==="
docker tag "$REPO_NAME:$IMAGE_TAG" "$ECR_URI/$REPO_NAME:$IMAGE_TAG"
docker push "$ECR_URI/$REPO_NAME:$IMAGE_TAG"

echo "=== Creating or updating App Runner service ==="
SERVICE_ARN=$(aws apprunner list-services --region "$REGION" --query "ServiceSummaryList[?ServiceName=='clinical-conversation-coach'].ServiceArn" --output text 2>/dev/null || echo "")

if [ -z "$SERVICE_ARN" ]; then
  echo "Creating new App Runner service..."
  aws apprunner create-service \
    --service-name clinical-conversation-coach \
    --source-configuration "ImageRepository={ImageIdentifier=$ECR_URI/$REPO_NAME:$IMAGE_TAG,ImageRepositoryType=ECR,ImageConfiguration={Port=8001,StartCommand='python -m server.mcp_server',RuntimeEnvironmentVariables=[{Name=MCP_HOST,Value=0.0.0.0},{Name=MCP_ALLOWED_HOSTS,Value=*}]}}" \
    --instance-configuration "Cpu=1 vCPU,Memory=2 GB" \
    --region "$REGION"
else
  echo "Updating existing App Runner service..."
  aws apprunner update-service \
    --service-arn "$SERVICE_ARN" \
    --source-configuration "ImageRepository={ImageIdentifier=$ECR_URI/$REPO_NAME:$IMAGE_TAG,ImageRepositoryType=ECR,ImageConfiguration={Port=8001,StartCommand='python -m server.mcp_server',RuntimeEnvironmentVariables=[{Name=MCP_HOST,Value=0.0.0.0},{Name=MCP_ALLOWED_HOSTS,Value=*}]}}" \
    --region "$REGION"
fi

echo "=== Done ==="
echo "Service URL will be available at: https://<random>.awsapprunner.com/mcp"
echo "Check status: aws apprunner describe-service --service-arn $SERVICE_ARN --region $REGION"
