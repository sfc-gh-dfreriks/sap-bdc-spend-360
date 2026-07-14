#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Build the Spend 360 container image and push it to a Snowflake image
# registry. Run once per region (US / EMEA / APAC).
#
# Usage:
#   ./build_and_push.sh <snowcli_connection> <registry_host>
#
# Example:
#   ./build_and_push.sh dfreriksdemo \
#       sfsenorthamerica-dfreriks-aws1-w2.registry.snowflakecomputing.com
#
# The image is pushed to:  <registry_host>/<repo_path>/spend_360:latest
# Adjust REPO_PATH to match your image repository.
# ---------------------------------------------------------------------------
set -euo pipefail

CONN="${1:?connection name required}"
REGISTRY_HOST="${2:?registry host required}"
REPO_PATH="${REPO_PATH:-sc360_app_provider/images/repo}"   # DB/SCHEMA/REPO, lowercased
IMAGE="${REGISTRY_HOST}/${REPO_PATH}/spend_360:latest"
CONTEXT="$(cd "$(dirname "$0")/../service/app" && pwd)"
PLATFORM="linux/amd64"

echo ">> Logging in to registry via connection '${CONN}'"
snow spcs image-registry login -c "${CONN}"

echo ">> Building + pushing ${IMAGE}"
docker buildx build --platform="${PLATFORM}" -t "${IMAGE}" --push "${CONTEXT}"

echo ">> Done: ${IMAGE}"
