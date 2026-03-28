#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="relieflink-hackathon"
IMAGE="us-docker.pkg.dev/${PROJECT_ID}/relieflink/${SERVICE_NAME}"

echo "Building Docker image..."
docker build -t "${IMAGE}" .

echo "Pushing to Artifact Registry..."
docker push "${IMAGE}"

echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 1 \
  --memory 1Gi \
  --timeout 300 \
  --set-secrets "GOOGLE_API_KEY=gemini-api-key:latest" \
  --port 8080

echo "Deployed: $(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')"
