#!/usr/bin/env bash
set -euo pipefail

# Deploy Clinical Conversation Coach to AWS App Runner from ECR.
# Prerequisites: AWS CLI configured, Docker installed.

REGION="${AWS_REGION:-us-east-2}"
# The `aws login` refresh token is bound to the region it was issued in.
# If you logged in with a plain `aws login` (no --region), it used your
# default region; that must match $REGION or the mid-deploy credential
# refresh fails (SignIn rejects redeeming a refresh token in a different
# region). Run `aws login --region "$REGION"` before deploying.
echo "=== Verifying AWS credentials in $REGION ==="
ACCOUNT_ID=$(aws sts get-caller-identity --region "$REGION" --query Account --output text)
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

# Emit the App Runner SourceConfiguration JSON to stdout. Secrets are passed as
# positional args to a Python heredoc and escaped there, so they never appear in
# the process command line. Keep this env list in sync with apprunner.yaml.
source_config_json() {
  local allowed_hosts="$1"
  python3 - "$ECR_URI/$REPO_NAME:$IMAGE_TAG" "$ACCESS_ROLE_ARN" "$allowed_hosts" \
    "${MCP_ALLOWED_ORIGINS:-http://127.0.0.1:*,http://localhost:*}" \
    "${MCP_API_KEY:-}" "${MCP_RATE_LIMIT_REQUESTS:-60}" "${MCP_RATE_LIMIT_WINDOW_SECONDS:-60}" \
    "${INFERENCE_PROVIDER:-mock}" "${BEDROCK_MODEL_ID:-}" "${AWS_REGION:-us-east-1}" \
    "${NIM_BASE_URL:-https://integrate.api.nvidia.com/v1}" "${NIM_API_KEY:-}" "${NIM_MODEL:-}" \
    "${CLOUDFLARE_BASE_URL:-}" "${CLOUDFLARE_API_KEY:-}" "${CLOUDFLARE_MODEL:-}" \
    "${SESSION_TTL_SECONDS:-1800}" "${SESSION_MAX_SESSIONS:-1000}" \
    "${SESSION_DB_PATH:-/tmp/sessions.db}" <<'PY'
import json
import sys

(image, role_arn, allowed_hosts, allowed_origins, api_key, rate_limit, rate_window,
 inference_provider, bedrock_model_id, aws_region,
 nim_base_url, nim_api_key, nim_model,
 cloudflare_base_url, cloudflare_api_key, cloudflare_model,
 session_ttl, session_max, session_db_path) = sys.argv[1:]

config = {
    "ImageRepository": {
        "ImageIdentifier": image,
        "ImageRepositoryType": "ECR",
        "ImageConfiguration": {
            "Port": "8001",
            "StartCommand": "python -m server.mcp_server",
            "RuntimeEnvironmentVariables": {
                "MCP_HOST": "0.0.0.0",
                "MCP_ALLOWED_HOSTS": allowed_hosts,
                "MCP_ALLOWED_ORIGINS": allowed_origins,
                "MCP_TRUST_PROXY": "true",
                "MCP_API_KEY": api_key,
                "MCP_RATE_LIMIT_REQUESTS": rate_limit,
                "MCP_RATE_LIMIT_WINDOW_SECONDS": rate_window,
                "INFERENCE_PROVIDER": inference_provider,
                "BEDROCK_MODEL_ID": bedrock_model_id,
                "AWS_REGION": aws_region,
                "NIM_BASE_URL": nim_base_url,
                "NIM_API_KEY": nim_api_key,
                "NIM_MODEL": nim_model,
                "CLOUDFLARE_BASE_URL": cloudflare_base_url,
                "CLOUDFLARE_API_KEY": cloudflare_api_key,
                "CLOUDFLARE_MODEL": cloudflare_model,
                "SESSION_TTL_SECONDS": session_ttl,
                "SESSION_MAX_SESSIONS": session_max,
                "SESSION_DB_PATH": session_db_path,
            },
        },
    },
    "AuthenticationConfiguration": {"AccessRoleArn": role_arn},
}

print(json.dumps(config))
PY
}

wait_for_running() {
  local arn="$1"
  echo "Waiting for service to reach RUNNING..."
  for _ in $(seq 1 40); do
    local status op_status
    # A transient credential-refresh failure must not abort the deploy: the
    # create/update call already succeeded server-side. Warn and keep polling.
    if ! status=$(aws apprunner describe-service --service-arn "$arn" --region "$REGION" --query Service.Status --output text 2>/dev/null); then
      echo "  (describe-service failed — credential session may have lapsed; the deploy was already submitted. Re-run 'aws login --region $REGION' and verify with: aws apprunner describe-service --service-arn $arn --region $REGION)" >&2
      sleep 30
      continue
    fi
    # A failed deployment leaves the service RUNNING on the previous image
    # (App Runner rolls back), so Service.Status alone would falsely report
    # success. Also inspect the latest operation.
    op_status=$(aws apprunner list-operations --service-arn "$arn" --region "$REGION" --query "OperationSummaryList[0].Status" --output text 2>/dev/null || echo "")
    echo "  status=$status operation=${op_status:-n/a}"
    case "$op_status" in
      FAILED|ROLLBACK_*)
        echo "Deployment failed (operation=$op_status); the previous image is still live." >&2
        return 1
        ;;
    esac
    case "$status" in
      RUNNING)
        case "$op_status" in
          ""|SUCCEEDED) return 0 ;;
          *) sleep 30; continue ;;
        esac
        ;;
      CREATE_FAILED|UPDATE_FAILED|DELETED) echo "Service entered $status" >&2; return 1 ;;
    esac
    sleep 30
  done
  echo "Could not confirm RUNNING within the timeout. Verify manually with: aws apprunner describe-service --service-arn $arn --region $REGION" >&2
  return 1
}

echo "=== Creating or updating App Runner service ==="
SERVICE_ARN=$(aws apprunner list-services --region "$REGION" --query "ServiceSummaryList[?ServiceName=='clinical-conversation-coach'].ServiceArn" --output text 2>/dev/null || echo "")
if [ -z "$SERVICE_ARN" ] || [ "$SERVICE_ARN" = "None" ]; then
  SERVICE_ARN=""
fi

# Secrets are written to a temp file and passed via --cli-input-json so they
# never appear in the process argv (visible via /proc) or AWS CLI error echo.
INPUT_FILE=$(mktemp)
trap 'rm -f "$INPUT_FILE"' EXIT

if [ -z "$SERVICE_ARN" ]; then
  echo "Creating new App Runner service..."
  {
    printf '{"ServiceName":"clinical-conversation-coach","SourceConfiguration":'
    source_config_json localhost
    printf ',"InstanceConfiguration":{"Cpu":"1 vCPU","Memory":"2 GB"}}'
  } > "$INPUT_FILE"
  CREATE_OUT=$(aws apprunner create-service --cli-input-json "file://$INPUT_FILE" --region "$REGION")
  SERVICE_ARN=$(echo "$CREATE_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Service']['ServiceArn'])")
  wait_for_running "$SERVICE_ARN"
fi

echo "=== Pinning host allowlist to the service URL ==="
SERVICE_URL=$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --region "$REGION" --query Service.ServiceUrl --output text)
SERVICE_HOST="${SERVICE_URL#https://}"
SERVICE_HOST="${SERVICE_HOST#http://}"
echo "Service host: $SERVICE_HOST"
{
  printf '{"ServiceArn":"%s","SourceConfiguration":' "$SERVICE_ARN"
  source_config_json "${SERVICE_HOST},${SERVICE_HOST}:*"
  printf '}'
} > "$INPUT_FILE"
aws apprunner update-service --cli-input-json "file://$INPUT_FILE" --region "$REGION" >/dev/null
wait_for_running "$SERVICE_ARN"

echo "=== Done ==="
echo "MCP endpoint: https://$SERVICE_HOST/mcp"
echo "Check status: aws apprunner describe-service --service-arn $SERVICE_ARN --region $REGION"
