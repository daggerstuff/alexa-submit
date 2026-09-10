#!/usr/bin/env bash
set -euo pipefail

# Deploy Clinical Conversation Coach to AWS App Runner from ECR.
# Prerequisites: AWS CLI configured, Docker installed.

REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME="clinical-conversation-coach"
# Unique tag per deploy so App Runner re-pulls the new image (a constant
# ":latest" reference does not trigger a new image pull).
IMAGE_TAG="${DEPLOY_TAG:-$(date +%Y%m%d%H%M%S)}"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
ACCESS_ROLE_NAME="apprunner-ecr-access-role"

if [[ -z "${MCP_API_KEY:-}" ]]; then
  echo "WARNING: MCP_API_KEY is not set. The public /mcp endpoint will be unauthenticated."
  echo "         Set MCP_API_KEY to a strong secret before deploying publicly."
fi

# Use sudo for the Docker daemon when the current user can't reach the socket.
DOCKER="docker"
if ! docker info >/dev/null 2>&1; then
  DOCKER="sudo docker"
fi

echo "=== Building Docker image ==="
$DOCKER build -t "$REPO_NAME:$IMAGE_TAG" .

echo "=== Creating ECR repository (if needed) ==="
aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$REGION" 2>/dev/null || \
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
aws ecr get-login-password --region "$REGION" | $DOCKER login --username AWS --password-stdin "$ECR_URI"

echo "=== Tagging and pushing image ==="
$DOCKER tag "$REPO_NAME:$IMAGE_TAG" "$ECR_URI/$REPO_NAME:$IMAGE_TAG"
$DOCKER push "$ECR_URI/$REPO_NAME:$IMAGE_TAG"

source_config_for_host() {
  local allowed_hosts="$1"
  local api_key="${MCP_API_KEY:-}"
  local rate_limit="${MCP_RATE_LIMIT_REQUESTS:-60}"
  local rate_window="${MCP_RATE_LIMIT_WINDOW_SECONDS:-60}"
  echo "ImageRepository={ImageIdentifier=$ECR_URI/$REPO_NAME:$IMAGE_TAG,ImageRepositoryType=ECR,ImageConfiguration={Port=8001,StartCommand='python -m server.mcp_server',RuntimeEnvironmentVariables={MCP_HOST=0.0.0.0,MCP_ALLOWED_HOSTS=$allowed_hosts,MCP_API_KEY=\"$api_key\",MCP_RATE_LIMIT_REQUESTS=$rate_limit,MCP_RATE_LIMIT_WINDOW_SECONDS=$rate_window}}},AuthenticationConfiguration={AccessRoleArn=$ACCESS_ROLE_ARN}"
}

wait_for_running() {
  local arn="$1"
  echo "Waiting for service to reach RUNNING..."
  for _ in $(seq 1 40); do
    local status
    status=$(aws apprunner describe-service --service-arn "$arn" --region "$REGION" --query Service.Status --output text)
    echo "  status=$status"
    case "$status" in
      RUNNING) return 0 ;;
      CREATE_FAILED|UPDATE_FAILED|DELETED) echo "Service entered $status" >&2; return 1 ;;
    esac
    sleep 30
  done
  echo "Timed out waiting for RUNNING" >&2
  return 1
}

echo "=== Creating or updating App Runner service ==="
SERVICE_ARN=$(aws apprunner list-services --region "$REGION" --query "ServiceSummaryList[?ServiceName=='clinical-conversation-coach'].ServiceArn" --output text 2>/dev/null || echo "")
if [ -z "$SERVICE_ARN" ] || [ "$SERVICE_ARN" = "None" ]; then
  SERVICE_ARN=""
fi

if [ -z "$SERVICE_ARN" ]; then
  echo "Creating new App Runner service..."
  CREATE_OUT=$(aws apprunner create-service \
    --service-name clinical-conversation-coach \
    --source-configuration "$(source_config_for_host localhost)" \
    --instance-configuration "Cpu=1 vCPU,Memory=2 GB" \
    --region "$REGION")
  SERVICE_ARN=$(echo "$CREATE_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Service']['ServiceArn'])")
  wait_for_running "$SERVICE_ARN"
fi

echo "=== Pinning host allowlist to the service URL ==="
SERVICE_URL=$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --region "$REGION" --query Service.ServiceUrl --output text)
SERVICE_HOST="${SERVICE_URL#https://}"
SERVICE_HOST="${SERVICE_HOST#http://}"
echo "Service host: $SERVICE_HOST"
aws apprunner update-service \
  --service-arn "$SERVICE_ARN" \
  --source-configuration "$(source_config_for_host "${SERVICE_HOST}\,${SERVICE_HOST}:*")" \
  --region "$REGION" >/dev/null
wait_for_running "$SERVICE_ARN"

echo "=== Done ==="
echo "MCP endpoint: https://$SERVICE_HOST/mcp"
echo "Check status: aws apprunner describe-service --service-arn $SERVICE_ARN --region $REGION"
