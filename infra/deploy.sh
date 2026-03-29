#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="us-central1"
SERVICE_NAME="relieflink"
IMAGE="gcr.io/${PROJECT_ID}/relieflink"
SECRET_NAME="${SECRET_NAME:-gemini-api-key}"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

run_step() {
  local description="$1"
  shift
  echo "${description}..."
  "$@" || fail "${description} failed."
}

command -v docker >/dev/null 2>&1 || fail "docker is not installed or not on PATH."
command -v gcloud >/dev/null 2>&1 || fail "gcloud is not installed or not on PATH."

run_step "Building Docker image ${IMAGE}" docker build -t "${IMAGE}" .
run_step "Pushing image ${IMAGE}" docker push "${IMAGE}"

echo "Deploying ${SERVICE_NAME} to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300 \
  --set-env-vars "PORT=8080,SERVICE_NAME=${SERVICE_NAME},GOOGLE_GENAI_USE_VERTEXAI=FALSE" \
  --set-secrets "GOOGLE_API_KEY=${SECRET_NAME}:latest" \
  --port 8080 \
  || fail "Cloud Run deployment failed."

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format 'value(status.url)')" \
  || fail "Fetching deployed Cloud Run service URL failed."

echo "Deploy complete."
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo "Image: ${IMAGE}"
echo "URL: ${SERVICE_URL}"
