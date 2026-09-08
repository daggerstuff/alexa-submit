#!/usr/bin/env bash
set -euo pipefail

# Deploy Clinical Conversation Coach to AWS App Runner from ECR.
# Prerequisites: AWS CLI configured, Docker installed.

REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME="clinical-conversation-coach"
IMAGE_TAG="latest"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
ACCESS_ROLE_NAME="apprunner-ecr-access-role"

echo "=== Building Docker image ==="
docker build -t "$REPO_NAME" .

echo "=== Creating ECR repository (if needed) ==="
aws ecr describe-repository --repository-name "$REPO_NAME" --region "$REGION" 2>/dev/null || \
  aws ecr create-repository --repository-name "$REPO_NAME" --region "$REGION"

echo "=== Ensuring App Runner ECR access role ==="
if ! aws iam get-role --role-name "$ACCESS_ROLE_NAME" 2>/dev/null; then
  aws iam create-role \
    --role-name "$ACCESS_ROLE_NAME" \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"build.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}' \
    --description "Allows App Runner to pull images from ECR"
  aws iam attach-role-policy \
    --role-name "$ACCESS_ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
  echo "Waiting for IAM role propagation..."
  sleep 10
fi
ACCESS_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ACCESS_ROLE_NAME}"

echo "=== Authenticating Docker to ECR ==="
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URI"

echo "=== Tagging and pushing image ==="
docker tag "$REPO_NAME:$IMAGE_TAG" "$ECR_URI/$REPO_NAME:$IMAGE_TAG"
docker push "$ECR_URI/$REPO_NAME:$IMAGE_TAG"

echo "=== Creating or updating App Runner service ==="
SERVICE_ARN=$(aws apprunner list-services --region "$REGION" --query "ServiceSummaryList[?ServiceName=='clinical-conversation-coach'].ServiceArn" --output text 2>/dev/null || echo "")
if [ -z "$SERVICE_ARN" ] || [ "$SERVICE_ARN" = "None" ]; then
  SERVICE_ARN=""
fi

SOURCE_CONFIG="ImageRepository={ImageIdentifier=$ECR_URI/$REPO_NAME:$IMAGE_TAG,ImageRepositoryType=ECR,ImageConfiguration={Port=8001,StartCommand='python -m server.mcp_server',RuntimeEnvironmentVariables=[{Name=MCP_HOST,Value=0.0.0.0},{Name=MCP_ALLOWED_HOSTS,Value=*}]}},AuthenticationConfiguration={AccessRoleArn=$ACCESS_ROLE_ARN}"

if [ -z "$SERVICE_ARN" ]; then
  echo "Creating new App Runner service..."
  aws apprunner create-service \
    --service-name clinical-conversation-coach \
    --source-configuration "$SOURCE_CONFIG" \
    --instance-configuration "Cpu=1 vCPU,Memory=2 GB" \
    --region "$REGION"
else
  echo "Updating existing App Runner service..."
  aws apprunner update-service \
    --service-arn "$SERVICE_ARN" \
    --source-configuration "$SOURCE_CONFIG" \
    --region "$REGION"
fi

echo "=== Done ==="
echo "Service URL will be available at: https://<random>.awsapprunner.com/mcp"
echo "Check status: aws apprunner describe-service --service-arn $SERVICE_ARN --region $REGION"
