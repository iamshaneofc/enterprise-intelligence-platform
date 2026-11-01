#!/usr/bin/env bash
# ==============================================================================
# Enterprise Intelligence Platform - Host-Level Secret Retrieval Script
# Fetches production secrets from AWS Secrets Manager using EC2 IAM Role
# Writes uncommitted, permission-restricted .env.production file for Docker Compose
# ==============================================================================
set -euo pipefail

SECRET_NAME="${SECRET_NAME:-eip/production/backend}"
AWS_REGION="${AWS_REGION:-ap-south-1}"
TARGET_ENV_FILE="${TARGET_ENV_FILE:-.env.production}"

echo "[INFO] Fetching secrets for '$SECRET_NAME' from region '$AWS_REGION'..."

# Verify prerequisite host tools
if ! command -v aws >/dev/null 2>&1; then
    echo "[ERROR] AWS CLI ('aws') is not installed on this host. Run: sudo apt-get install -y awscli" >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "[ERROR] 'jq' is not installed on this host. Run: sudo apt-get install -y jq" >&2
    exit 1
fi

# Fetch secret payload from AWS Secrets Manager using IAM Instance Role
SECRET_PAYLOAD=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" \
    --query 'SecretString' \
    --output text 2>/dev/null || true)

if [ -z "$SECRET_PAYLOAD" ] || [ "$SECRET_PAYLOAD" = "null" ]; then
    echo "[ERROR] Failed to retrieve secret '$SECRET_NAME' from AWS Secrets Manager." >&2
    echo "[ERROR] Confirm that the EC2 IAM Instance Profile is attached and allows 'secretsmanager:GetSecretValue'." >&2
    exit 1
fi

# Write key-value pairs to uncommitted target file
echo "# Auto-generated from AWS Secrets Manager ($SECRET_NAME) on $(date -u +"%Y-%m-%dT%H:%M:%SZ")" > "$TARGET_ENV_FILE"
echo "$SECRET_PAYLOAD" | jq -r 'to_entries | map("\(.key)=\(.value|tostring)") | .[]' >> "$TARGET_ENV_FILE"

# Set strict file permissions (read/write only by owner)
chmod 600 "$TARGET_ENV_FILE"

# Validate that target file is non-empty without printing contents
if [ -s "$TARGET_ENV_FILE" ]; then
    KEY_COUNT=$(wc -l < "$TARGET_ENV_FILE")
    echo "[SUCCESS] Successfully generated '$TARGET_ENV_FILE' with $KEY_COUNT entries (permissions: 0600)."
    echo "[INFO] You can now start containers using: docker compose --env-file $TARGET_ENV_FILE up -d --build"
else
    echo "[ERROR] Generated file '$TARGET_ENV_FILE' is empty." >&2
    exit 1
fi
