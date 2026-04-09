# Deployment Guide — Google Cloud Platform

Five a Day runs on GCP using **Cloud Run** (container hosting) + **Cloud SQL** (PostgreSQL). The project already uses Google OAuth and Gmail SMTP, so GCP integration is natural.

---

## Architecture on GCP

```
Internet → Cloud Run (Django/Gunicorn) → Cloud SQL (PostgreSQL 16)
                ↓
           Gmail SMTP (email sending via app password)
           Google OAuth (admin login)
```

- **Cloud Run**: Serves the Django app in a Docker container. Auto-scales (min 0, max 2 for this scale). Uses the project's `Dockerfile` as-is.
- **Cloud SQL**: Managed PostgreSQL 16. Automatic backups, patching. Connected via Cloud SQL Auth Proxy (built into Cloud Run).
- **Static files**: Served by WhiteNoise from the Django container (no separate CDN needed at this scale).
- **Secrets**: Stored in GCP Secret Manager, injected as env vars into Cloud Run.

---

## Prerequisites

1. **GCP project** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Docker** installed locally
4. A **Gmail account** with an app password for SMTP
5. **Google OAuth credentials** (client ID + secret) from Google Cloud Console

---

## Initial Setup

### 1. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### 2. Create Cloud SQL instance

```bash
gcloud sql instances create fiveaday-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=europe-southwest1 \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=03:00 \
  --availability-type=zonal

# Create database and user
gcloud sql databases create fiveaday_db --instance=fiveaday-db
gcloud sql users create fiveaday_user --instance=fiveaday-db --password=YOUR_SECURE_PASSWORD
```

### 3. Create Artifact Registry repository

```bash
gcloud artifacts repositories create fiveaday \
  --repository-format=docker \
  --location=europe-southwest1
```

### 4. Store secrets in Secret Manager

```bash
# Create each secret
echo -n "your-django-secret-key" | gcloud secrets create DJANGO_SECRET_KEY --data-file=-
echo -n "your-db-password" | gcloud secrets create POSTGRES_PASSWORD --data-file=-
echo -n "your-gmail@gmail.com" | gcloud secrets create EMAIL_HOST_USER --data-file=-
echo -n "your-gmail-app-password" | gcloud secrets create EMAIL_SECRET --data-file=-
echo -n "your-google-client-id" | gcloud secrets create GOOGLE_CLIENT_ID --data-file=-
echo -n "your-google-client-secret" | gcloud secrets create GOOGLE_CLIENT_SECRET --data-file=-
echo -n "your-login-password" | gcloud secrets create LOGIN_PASSWORD --data-file=-
```

---

## Build & Deploy

### Build and push Docker image

```bash
# Set variables
PROJECT_ID=$(gcloud config get-value project)
REGION=europe-southwest1
IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/fiveaday/web

# Build and push
gcloud builds submit --tag $IMAGE .
```

### Deploy to Cloud Run

```bash
gcloud run deploy fiveaday \
  --image=$IMAGE \
  --platform=managed \
  --region=$REGION \
  --port=8000 \
  --min-instances=0 \
  --max-instances=2 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=120 \
  --allow-unauthenticated \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:fiveaday-db \
  --set-env-vars="DJANGO_ENV=production" \
  --set-env-vars="DJANGO_DEBUG=False" \
  --set-env-vars="DJANGO_ALLOWED_HOSTS=fiveaday-XXXXX-ew.a.run.app" \
  --set-env-vars="DATABASE_URL=postgres://fiveaday_user:PASSWORD@/fiveaday_db?host=/cloudsql/$PROJECT_ID:$REGION:fiveaday-db" \
  --set-env-vars="LOGIN_USERNAME=fiveaday" \
  --set-env-vars="GOOGLE_REDIRECT_URI=https://fiveaday-XXXXX-ew.a.run.app/auth/google/callback/" \
  --set-secrets="DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest" \
  --set-secrets="EMAIL_HOST_USER=EMAIL_HOST_USER:latest" \
  --set-secrets="EMAIL_SECRET=EMAIL_SECRET:latest" \
  --set-secrets="GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest" \
  --set-secrets="GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest" \
  --set-secrets="LOGIN_PASSWORD=LOGIN_PASSWORD:latest"
```

After the first deploy, note the Cloud Run URL (e.g., `https://fiveaday-abc123-ew.a.run.app`) and update:
- `DJANGO_ALLOWED_HOSTS` with the actual URL
- `GOOGLE_REDIRECT_URI` with `https://YOUR_URL/auth/google/callback/`
- Google OAuth console: add the redirect URI to authorized redirect URIs

### Run migrations (first deploy only)

```bash
gcloud run jobs create fiveaday-migrate \
  --image=$IMAGE \
  --region=$REGION \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:fiveaday-db \
  --set-env-vars="DATABASE_URL=postgres://fiveaday_user:PASSWORD@/fiveaday_db?host=/cloudsql/$PROJECT_ID:$REGION:fiveaday-db" \
  --command="python" \
  --args="project/manage.py,migrate"

gcloud run jobs execute fiveaday-migrate --region=$REGION --wait
```

---

## Updating (Routine Deploys)

```bash
# Build new image
gcloud builds submit --tag $IMAGE .

# Deploy (Cloud Run will do a rolling update)
gcloud run deploy fiveaday --image=$IMAGE --region=$REGION

# Run migrations if models changed
gcloud run jobs execute fiveaday-migrate --region=$REGION --wait
```

---

## Custom Domain

```bash
# Map your domain
gcloud run domain-mappings create \
  --service=fiveaday \
  --domain=app.fiveadayenglish.com \
  --region=$REGION
```

Follow the DNS instructions from the output (add CNAME record to your domain provider).

Update `DJANGO_ALLOWED_HOSTS` to include the custom domain.

---

## Monitoring & Maintenance

### View logs

```bash
# Tail live logs
gcloud run services logs tail fiveaday --region=$REGION

# Search recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=fiveaday" --limit=50
```

### Database backups

Cloud SQL performs automatic daily backups (configured at 03:00). To create a manual backup:

```bash
gcloud sql backups create --instance=fiveaday-db
```

To restore from a backup:

```bash
gcloud sql backups list --instance=fiveaday-db
gcloud sql backups restore BACKUP_ID --restore-instance=fiveaday-db
```

### Database shell (Cloud SQL Proxy)

```bash
# Install Cloud SQL Auth Proxy
gcloud sql connect fiveaday-db --user=fiveaday_user --database=fiveaday_db
```

### Django management commands

Run one-off commands using Cloud Run Jobs:

```bash
# Django shell (interactive — use local with proxy instead)
# For non-interactive commands:
gcloud run jobs create fiveaday-cmd \
  --image=$IMAGE \
  --region=$REGION \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:fiveaday-db \
  --set-env-vars="DATABASE_URL=..." \
  --command="python" \
  --args="project/manage.py,generate_payments,--month,10,--year,2025"

gcloud run jobs execute fiveaday-cmd --region=$REGION --wait
```

---

## Cost Estimate (Small Academy)

| Service | Tier | Monthly Cost |
| ------- | ---- | ------------ |
| Cloud Run | min 0, max 2 instances, 512Mi | ~$5-15 |
| Cloud SQL | db-f1-micro, 10GB | ~$10 |
| Secret Manager | 6 secrets | < $1 |
| Artifact Registry | < 1GB images | < $1 |
| **Total** | | **~$15-25/month** |

With Cloud Run's scale-to-zero, costs are minimal when the app isn't being used.

---

## Troubleshooting

### "could not translate host name 'db'"

The app is trying to connect to the Docker hostname `db` instead of Cloud SQL. Ensure `DATABASE_URL` is set in Cloud Run env vars (it takes priority over the Docker-oriented `.env` values).

### Static files 404

Run `collectstatic` as a Cloud Run Job or ensure the Dockerfile's entrypoint runs it. The project's `Dockerfile` already does this via `entrypoint.sh`.

### Google OAuth callback mismatch

Ensure `GOOGLE_REDIRECT_URI` in Cloud Run matches exactly what's configured in Google Cloud Console > OAuth credentials > Authorized redirect URIs. Include the trailing slash.

### Slow cold starts

Cloud Run containers take 5-10 seconds on cold start. Set `--min-instances=1` if you need instant responses (adds ~$25/month).
