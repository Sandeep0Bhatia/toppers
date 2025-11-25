#!/bin/bash

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-true-solstice-475115-f6}"
REGION="us-central1"
JOB_NAME="toppers-daily-job"
IMAGE_NAME="toppers-daily-job"
SERVICE_ACCOUNT="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Deploying Toppers job to Google Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Job: $JOB_NAME"

# Build Docker image
echo "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME:latest .

# Push to Google Container Registry
echo "Pushing to GCR..."
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:latest

# Deploy or update Cloud Run Job
echo "Updating Cloud Run Job..."
if gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "Job exists, updating..."
    gcloud run jobs update $JOB_NAME \
        --image=gcr.io/$PROJECT_ID/$IMAGE_NAME:latest \
        --region=$REGION \
        --project=$PROJECT_ID \
        --max-retries=1 \
        --task-timeout=30m \
        --memory=4Gi \
        --cpu=2 \
        --set-env-vars="$(cat .env | grep -v '^#' | grep -v '^$' | tr '\n' ',' | sed 's/,$//')" \
        --service-account=$SERVICE_ACCOUNT
else
    echo "Job does not exist, creating..."
    gcloud run jobs create $JOB_NAME \
        --image=gcr.io/$PROJECT_ID/$IMAGE_NAME:latest \
        --region=$REGION \
        --project=$PROJECT_ID \
        --max-retries=1 \
        --task-timeout=30m \
        --memory=4Gi \
        --cpu=2 \
        --set-env-vars="$(cat .env | grep -v '^#' | grep -v '^$' | tr '\n' ',' | sed 's/,$//')" \
        --service-account=$SERVICE_ACCOUNT
fi

echo "Deployment complete!"
echo ""
echo "To execute the job manually:"
echo "  gcloud run jobs execute $JOB_NAME --region=$REGION --project=$PROJECT_ID"
echo ""
echo "To view logs:"
echo "  gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME\" --limit=50 --project=$PROJECT_ID"
