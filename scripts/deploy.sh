#!/bin/bash
# Nexus AI — Cloud Run Deployment Script
# Usage: export GCP_PROJECT_ID=your-id && ./scripts/deploy.sh

set -e

# This prevents the "your-project-id" placeholder bug
if [[ -z "${GCP_PROJECT_ID}" ]]; then
  echo " Error: GCP_PROJECT_ID is not set."
  echo "Run: export GCP_PROJECT_ID='your-actual-project-id'"
  exit 1
fi

if [[ -z "${CLOUDSQL_INSTANCE}" ]]; then
  echo " Error: CLOUDSQL_INSTANCE is not set."
  echo "Run: export CLOUDSQL_INSTANCE='project:region:instance'"
  exit 1
fi

PROJECT_ID="${GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="nexus-ai"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
CLOUDSQL_CONNECTION="${CLOUDSQL_INSTANCE}"
DB_NAME="${DB_NAME:-nexus_db}"
DB_USER="${DB_USER:-nexus_user}"

echo "🚀 Deploying Nexus AI to Cloud Run"
echo "   Project:  ${PROJECT_ID}"
echo "   Region:   ${REGION}"
echo "   Image:    ${IMAGE_NAME}"
echo "   CloudSQL: ${CLOUDSQL_CONNECTION}"
echo "   Database: ${DB_NAME}"
echo ""

echo " Setting gcloud project context..."
gcloud config set project "${PROJECT_ID}"

# Note: Ensure your .gcloudignore does NOT include your app/ directory
echo " Building container via Cloud Build..."
gcloud builds submit --tag "${IMAGE_NAME}:latest" .

echo "☁️  Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}:latest" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --concurrency 80 \
    --add-cloudsql-instances "${CLOUDSQL_CONNECTION}" \
    --set-env-vars "APP_ENV=production" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GCP_REGION=${REGION}" \
    --set-env-vars "CLOUDSQL_INSTANCE_CONNECTION_NAME=${CLOUDSQL_CONNECTION}" \
    --set-env-vars "DB_NAME=${DB_NAME}" \
    --set-env-vars "DB_USER=${DB_USER}" \
    --set-secrets "GEMINI_API_KEY=nexus-gemini-key:latest" \
    --set-secrets "DB_PASSWORD=nexus-db-password:latest" \
    --set-secrets "ASANA_ACCESS_TOKEN=nexus-asana-token:latest" \
    --set-secrets "SLACK_BOT_TOKEN=nexus-slack-token:latest" \
    --set-secrets "GOOGLE_CLIENT_ID=nexus-google-client-id:latest" \
    --set-secrets "GOOGLE_CLIENT_SECRET=nexus-google-client-secret:latest"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region "${REGION}" \
    --format "value(status.url)")

echo ""
echo "✅ Deployment complete!"
echo "   Service URL: ${SERVICE_URL}"
echo "   Health:      ${SERVICE_URL}/health"
echo "   API Docs:    ${SERVICE_URL}/docs"
