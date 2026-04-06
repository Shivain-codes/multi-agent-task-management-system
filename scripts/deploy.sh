set -e
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="nexus-ai"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
VPC_CONNECTOR="${VPC_CONNECTOR:-alloydb-connector}"   # reuse from mini project

echo "🚀 Deploying Nexus AI to Cloud Run"
echo "   Project: ${PROJECT_ID}"
echo "   Region:  ${REGION}"
echo "   Image:   ${IMAGE_NAME}"
echo ""

gcloud config set project "${PROJECT_ID}"

echo "📦 Building container..."
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
    --vpc-connector "${VPC_CONNECTOR}" \
    --vpc-egress private-ranges-only \
    --set-env-vars "APP_ENV=production" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GCP_REGION=${REGION}" \
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
echo " Deployment complete!"
echo "   Service URL: ${SERVICE_URL}"
echo "   Health:      ${SERVICE_URL}/health"
echo "   API Docs:    ${SERVICE_URL}/docs"
echo "   Run workflow: curl -X POST ${SERVICE_URL}/api/v1/workflows/run \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"request\": \"Plan a product launch for next Friday\"}'"
