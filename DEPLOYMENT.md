# Deployment Guide — Google Cloud Platform

Five a Day runs on three environments with different cost and complexity trade-offs.

---

## Environments at a Glance

|                   | Development         | Testing                        | Production                  |
|-------------------|---------------------|--------------------------------|-----------------------------|
| **Where**         | Local machine       | GCP Compute Engine (free tier) | GCP Cloud Run               |
| **Database**      | Docker (PostgreSQL) | Docker (PostgreSQL)            | Cloud SQL (PostgreSQL 16)   |
| **Celery**        | Docker (full stack) | Docker (full stack)            | Eager mode + Cloud Scheduler|
| **Static files**  | Django runserver    | WhiteNoise                     | WhiteNoise                  |
| **HTTPS**         | No                  | No                             | Cloud Run (automatic)       |
| **Cost**          | $0                  | **$0** (permanent free tier)   | ~$15–27/month               |

---

## 1. Development (Local)

No cloud resources needed. Everything runs in Docker, identical to production services.

```bash
uv sync --no-install-project   # Install dependencies
make up                         # Start PostgreSQL + Django + Redis + Celery
make test                       # Run test suite against PostgreSQL
```

---

## 2. Testing (Compute Engine — Free)

The testing environment runs on a **GCP Compute Engine e2-micro**, which is permanently free. It uses
the same `docker-compose.yml` as development — no cloud-native services needed.

### Why a VM instead of Cloud Run

- Free forever under GCP's always-free tier
- Identical to the local docker-compose — no surprises, no refactoring
- Acceptable to be slow or restart — dummy data only, no real users
- 30-40 students and 200 payments fit easily in 1 GB RAM with a swap file

### Limitations

- The e2-micro free tier requires a US region (`us-east1`, `us-west1`, or `us-central1`). From Spain
  this means ~150ms latency, which is acceptable for testing purposes.
- 1 GB RAM is tight with all five containers running. A swap file is required (see below).
- The testing database is completely isolated from production — different host, different credentials.

### VM setup

#### 1. Create the instance

```bash
gcloud compute instances create fiveaday-testing \
  --zone=us-east1-b \
  --machine-type=e2-micro \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard \
  --tags=http-server
```

#### 2. SSH in and install Docker

```bash
gcloud compute ssh fiveaday-testing --zone=us-east1-b
```

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
sudo systemctl enable docker
```

#### 3. Add a swap file (required)

1 GB RAM is not enough for all five containers plus the OS. A 2 GB swap file brings the effective
memory to 3 GB, which is plenty for testing workloads.

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verify with `free -h` — you should see ~2 GB in the Swap row.

#### 4. Deploy the app

```bash
git clone https://github.com/YOUR_ORG/five-a-day.git
cd five-a-day
# Create .env.testing and populate it using the template in README.md (section ".env template")
touch .env.testing
docker compose --env-file .env.testing up -d
```

Because docker-compose uses `restart: unless-stopped`, all containers come back automatically after a
VM reboot — no manual intervention needed.

#### 5. Routine updates

```bash
git pull
docker compose down
docker compose up -d --build
```

### Free tier limits (permanent, never expire)

| Resource          | Free allowance          | Your usage  |
|-------------------|-------------------------|-------------|
| e2-micro instance | 1 instance/month        | 1 instance  |
| Persistent disk   | 30 GB standard          | 30 GB       |
| Network egress    | 1 GB/month (to internet)| < 1 GB      |

**Cost: $0/month, permanently.**

---

## 3. Production (Cloud Run + Cloud SQL)

### Architecture

```
Internet
  → Cloud Run (Django/Gunicorn, 1 vCPU, 512 MB, min-0 or min-1)
      → Cloud SQL Auth Proxy → Cloud SQL (PostgreSQL 16, db-f1-micro, 10 GB)
      → Gmail SMTP (transactional email via App Password)
      → Google OAuth (admin authentication)

Cloud Scheduler (cron jobs — replaces Celery Beat)
  → Cloud Run Jobs (management commands — one job per scheduled task)

GCP Secret Manager → env vars injected into Cloud Run at startup
Artifact Registry  → Docker images built by Cloud Build
Cloud DNS          → Custom domain → Cloud Run (TLS auto-managed)
```

**Nginx is not needed.** Cloud Run handles TLS termination, load balancing, and HTTP/2 natively.
WhiteNoise serves static files directly from the Django container.

### Celery strategy on Cloud Run

Cloud Run containers must respond to HTTP — long-running Celery worker processes cannot run there.
This is solved in two layers:

**Async tasks** (email sends triggered by user actions, PDF generation):
Set `CELERY_TASK_ALWAYS_EAGER=True` in production. Tasks run synchronously inside the HTTP request.
Imperceptible for 4 teachers and occasional sends. No Redis or worker process needed.

**Periodic tasks** (Celery Beat — birthday emails, payment reminders, scheduled reports):
Use **Cloud Scheduler** to trigger **Cloud Run Jobs** that execute Django management commands.
Each Beat schedule becomes one Scheduler job. Setup is covered in the [Celery Beat section](#celery-beat--cloud-scheduler) below.

### Prerequisites

1. GCP project with billing enabled
2. `gcloud` CLI installed and authenticated (`gcloud auth login`)
3. Docker installed locally
4. Gmail account with an App Password for SMTP
5. Google OAuth credentials (Client ID + Secret) from Google Cloud Console

### Initial setup

#### 1. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  dns.googleapis.com
```

#### 2. Create Cloud SQL instance

```bash
gcloud sql instances create fiveaday-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=europe-southwest1 \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=03:00 \
  --availability-type=zonal

gcloud sql databases create fiveaday_db --instance=fiveaday-db
gcloud sql users create fiveaday_user \
  --instance=fiveaday-db \
  --password=YOUR_SECURE_PASSWORD
```

**Why 10 GB**: With HistoryLog capped at 1,000 rows, the database grows slowly. Payment history for
1,000 students over 20 years (~360,000 rows) plus all other tables totals under 1 GB. 10 GB provides
a decade of headroom with auto-increase as a safety net.

#### 3. Create Artifact Registry repository

```bash
gcloud artifacts repositories create fiveaday \
  --repository-format=docker \
  --location=europe-southwest1
```

#### 4. Store secrets in Secret Manager

```bash
echo -n "your-django-secret-key"    | gcloud secrets create DJANGO_SECRET_KEY    --data-file=-
echo -n "your-db-password"          | gcloud secrets create POSTGRES_PASSWORD     --data-file=-
echo -n "your-gmail@gmail.com"      | gcloud secrets create EMAIL_HOST_USER       --data-file=-
echo -n "your-gmail-app-password"   | gcloud secrets create EMAIL_SECRET          --data-file=-
echo -n "your-google-client-id"     | gcloud secrets create GOOGLE_CLIENT_ID      --data-file=-
echo -n "your-google-client-secret" | gcloud secrets create GOOGLE_CLIENT_SECRET  --data-file=-
echo -n "your-login-password"       | gcloud secrets create LOGIN_PASSWORD        --data-file=-
```

### Build & Deploy

```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=europe-southwest1
IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/fiveaday/web

# Build and push image
gcloud builds submit --tag $IMAGE .

# Deploy
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
  --set-env-vars="CELERY_TASK_ALWAYS_EAGER=True" \
  --set-env-vars="GOOGLE_REDIRECT_URI=https://fiveaday-XXXXX-ew.a.run.app/auth/google/callback/" \
  --set-secrets="DJANGO_SECRET_KEY=DJANGO_SECRET_KEY:latest" \
  --set-secrets="EMAIL_HOST_USER=EMAIL_HOST_USER:latest" \
  --set-secrets="EMAIL_SECRET=EMAIL_SECRET:latest" \
  --set-secrets="GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest" \
  --set-secrets="GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest" \
  --set-secrets="LOGIN_PASSWORD=LOGIN_PASSWORD:latest"
```

After the first deploy, note the Cloud Run URL (e.g., `https://fiveaday-abc123-ew.a.run.app`) and
update:
- `DJANGO_ALLOWED_HOSTS` with the actual URL
- `GOOGLE_REDIRECT_URI` with `https://YOUR_URL/auth/google/callback/`
- Google Cloud Console → OAuth credentials → Authorized redirect URIs (add the callback URL)

### Run migrations

Required on first deploy and after any model change:

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

On subsequent deploys with model changes, just run the job again:

```bash
gcloud run jobs execute fiveaday-migrate --region=$REGION --wait
```

### Celery Beat → Cloud Scheduler

Each Celery Beat periodic task becomes a Cloud Scheduler job that triggers a Cloud Run Job running a
Django management command. This requires no changes to the existing management commands.

#### Step 1 — Create a reusable Cloud Run Job per task

```bash
# Example: generate monthly payments
gcloud run jobs create fiveaday-generate-payments \
  --image=$IMAGE \
  --region=$REGION \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:fiveaday-db \
  --set-env-vars="DATABASE_URL=..." \
  --command="python" \
  --args="project/manage.py,generate_payments"

# Example: send birthday emails
gcloud run jobs create fiveaday-birthday-emails \
  --image=$IMAGE \
  --region=$REGION \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:fiveaday-db \
  --set-env-vars="DATABASE_URL=..." \
  --command="python" \
  --args="project/manage.py,send_birthday_emails"
```

Repeat for each periodic task. Reuse the same `--image` and `--add-cloudsql-instances` flags.

#### Step 2 — Schedule each job with Cloud Scheduler

Cloud Scheduler triggers the Cloud Run Jobs API to execute a job on a cron schedule.

```bash
# Get the service account Cloud Run uses (or create a dedicated one)
SA=fiveaday-scheduler@$PROJECT_ID.iam.gserviceaccount.com

gcloud iam service-accounts create fiveaday-scheduler \
  --display-name="Five a Day Scheduler"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA" \
  --role="roles/run.invoker"

# Schedule: generate payments on the 1st of every month at 08:00 Madrid time
gcloud scheduler jobs create http fiveaday-generate-payments \
  --location=$REGION \
  --schedule="0 8 1 * *" \
  --time-zone="Europe/Madrid" \
  --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/fiveaday-generate-payments:run" \
  --message-body="{}" \
  --oauth-service-account-email=$SA

# Schedule: birthday emails daily at 07:00
gcloud scheduler jobs create http fiveaday-birthday-emails \
  --location=$REGION \
  --schedule="0 7 * * *" \
  --time-zone="Europe/Madrid" \
  --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/fiveaday-birthday-emails:run" \
  --message-body="{}" \
  --oauth-service-account-email=$SA
```

Repeat for each periodic task. The first 3 Scheduler jobs per month are free; beyond that it is
$0.10/job/month — 20 jobs costs **$1.70/month**.

### Custom domain

```bash
gcloud run domain-mappings create \
  --service=fiveaday \
  --domain=app.yourdomain.com \
  --region=$REGION
```

The command outputs DNS records to add at your domain registrar (a CNAME or A record). Cloud Run
issues and renews the TLS certificate automatically. Then update `DJANGO_ALLOWED_HOSTS` to include
the custom domain and redeploy.

**Domain options:**

- External registrar (Namecheap, Porkbun): ~€10-15/year for `.com` or `.es`, point a CNAME to the
  Cloud Run URL.
- Cloud Domains (in GCP): ~$12/year, DNS managed automatically within GCP.

### Routine deploys

```bash
# Build new image
gcloud builds submit --tag $IMAGE .

# Deploy (Cloud Run performs a rolling update with zero downtime)
gcloud run deploy fiveaday --image=$IMAGE --region=$REGION

# Run migrations if any models changed
gcloud run jobs execute fiveaday-migrate --region=$REGION --wait
```

### Monitoring & maintenance

```bash
# Tail live logs
gcloud run services logs tail fiveaday --region=$REGION

# Search recent logs
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=fiveaday" \
  --limit=50

# Manual database backup
gcloud sql backups create --instance=fiveaday-db

# List backups
gcloud sql backups list --instance=fiveaday-db

# Restore from a backup
gcloud sql backups restore BACKUP_ID --restore-instance=fiveaday-db

# Run any Django management command on production data
gcloud run jobs create fiveaday-cmd \
  --image=$IMAGE \
  --region=$REGION \
  --add-cloudsql-instances=$PROJECT_ID:$REGION:fiveaday-db \
  --set-env-vars="DATABASE_URL=..." \
  --command="python" \
  --args="project/manage.py,YOUR_COMMAND,--arg1,value1"

gcloud run jobs execute fiveaday-cmd --region=$REGION --wait
```

---

## 4. Cost Estimates

### GCP free credits — first 90 days

New GCP accounts receive **$300 USD in free credits, valid for 90 days**. At ~$15-27/month for
production, you will consume roughly $45-80 of the $300 before the window closes. The remaining
balance expires unused — credits cannot be extended or saved.

Use the free period to set up the production environment, validate Cloud Run + Cloud SQL integration,
configure secrets, domain, OAuth, and Cloud Scheduler jobs without spending real money.

### Permanent free tiers (never expire)

These quotas reset monthly and apply to all GCP accounts regardless of age:

| Service            | Free allowance per month             | Your usage                    |
|--------------------|--------------------------------------|-------------------------------|
| Compute Engine     | 1 e2-micro instance (US regions)     | Testing VM                    |
| Cloud Run          | 2M req + 180K vCPU-sec + 360K GB-sec | ~96K requests, ~29K vCPU-sec  |
| Cloud Build        | 120 build-minutes/day                | A few deploys/month           |
| Cloud Scheduler    | 3 jobs                               | First 3 periodic tasks        |
| Cloud Tasks        | 1M task executions                   | All async email sends         |
| Secret Manager     | 10K access operations                | ~100 ops                      |
| Artifact Registry  | 0.5 GB storage                       | ~0.5 GB Docker image          |
| Cloud Logging      | 50 GB ingestion                      | Well under                    |

Cloud Run's free tier alone covers **all traffic for 4 teachers** — the Django app itself costs
effectively $0 in compute. The unavoidable cost is Cloud SQL (always running, always charged).

### Ongoing monthly costs (production — after credits expire)

| Service                        | Config                              | Cost/month  |
|--------------------------------|-------------------------------------|-------------|
| Cloud Run (cold starts OK)     | 1 vCPU, 512 MB, min-0, max-2        | ~$0–2       |
| Cloud Run (always warm)        | same, min-1                         | ~$7–10      |
| Cloud SQL                      | db-f1-micro, 10 GB, daily backups   | ~$10–12     |
| Cloud Scheduler                | 20 jobs (17 beyond free 3)          | ~$1.70      |
| Cloud Tasks                    | async email queue                   | <$1         |
| Secret Manager + Artifact Reg. | 8 secrets, <1 GB images             | <$1         |
| Cloud DNS                      | 1 managed zone                      | ~$0.50      |
| **Total (min-0)**              |                                     | **~$15–18** |
| **Total (min-1, always warm)** |                                     | **~$22–27** |

Testing VM and local development: **$0/month**.

**min-0 vs min-1**: With `min-instances=0`, the container shuts down after inactivity. The first
request of the day takes 5-10 seconds (cold start). With `min-instances=1`, it stays warm 24/7 at
~$7/month. You can toggle this live without redeploying:

```bash
gcloud run services update fiveaday --min-instances=1 --region=$REGION
```

---

## 5. Optional Services for Future Evolution

These are not needed at launch. They are the natural next steps as the system or user base grows.

### Cloud Monitoring + uptime alerts

Set up uptime checks so you are notified before teachers notice the app is down. No code changes
needed.

```bash
# Create an uptime check on the health endpoint
gcloud monitoring uptime-check-configs create http \
  --display-name="Five a Day uptime" \
  --http-check-path="/_health/" \
  --hostname=app.yourdomain.com
```

Cost: free for basic checks. Email alert notifications are free. Recommended as soon as the app
goes to production.

### Cloud Storage (GCS) — media files and bulk exports

Cloud Run containers have an ephemeral filesystem — any file written during a request is lost after
the container restarts. If you add student photo uploads, document storage, or bulk PDF/Excel
exports meant for download, those files need to live in Cloud Storage.

```bash
gcloud storage buckets create gs://fiveaday-media --location=europe-southwest1
```

`django-storages` (already a project dependency) supports GCS with minimal settings changes.

Cost: ~$0.02/GB/month. At this scale, effectively free.

### Sendgrid or Mailgun — high-volume email

Gmail SMTP allows 500 emails/day via App Password. This covers the current workload comfortably.
If you run large campaigns (announcements to all 1,000 students' families, bulk payment reminders),
you will hit that limit.

Sendgrid free tier: 100 emails/day. Paid: from ~$20/month for 50K emails/month. No code changes
needed — update `EMAIL_BACKEND` and credentials in Secret Manager.

### Cloud Armor — web application firewall

Protects against DDoS attacks and common web exploits (OWASP Top 10). Not justified for an
internal academy tool with 4 known users, but relevant if you ever open the app to students or
parents directly.

Cost: ~$6/month base + $0.75/million requests.

### Cloud CDN — static file acceleration

If you serve a student or parent portal with many simultaneous users downloading assets, a CDN in
front of static files reduces latency and Cloud Run load. WhiteNoise is sufficient at the current
scale.

Cost: ~$0.02/GB egress.

### Memorystore (Redis) — full async Celery

If the `CELERY_TASK_ALWAYS_EAGER` approach causes slow HTTP responses (e.g., a task that takes 10+
seconds) and the Cloud Scheduler/Tasks migration is not worth implementing, Memorystore is a managed
Redis that the existing Celery architecture connects to without code changes. Run the Celery worker
as a separate always-on Cloud Run service with a lightweight health check endpoint.

Cost: ~$20-25/month for the 1 GB basic tier. Only worth it if other options are exhausted.

### Vertex AI — intelligent features

The existing data model (students, payments, attendance, history) is well-suited for ML features:
automatic payment risk scoring, attendance pattern analysis, or natural language report generation.
Vertex AI provides managed models and pipelines when you are ready to explore this.

Cost: varies by usage and model.

### Cloud SQL read replica — reporting queries

If heavy reporting queries (bulk exports, analytics dashboards) start causing slow responses for
teachers, a read replica lets reporting queries run against a separate instance without affecting
the primary. At the current scale of 4 users this is not needed.

Cost: same tier as primary (~$10-12/month additional).

---

## Troubleshooting

### "could not translate host name 'db'"

The app is connecting to the Docker hostname `db` instead of Cloud SQL. Ensure `DATABASE_URL` is
set in Cloud Run env vars — it takes priority over any `.env` file values.

### Static files returning 404

The `entrypoint.sh` runs `collectstatic` automatically when `DJANGO_ENV=production` is set. If
static files are missing, confirm that env var is present in the Cloud Run service configuration.

### Google OAuth callback mismatch

`GOOGLE_REDIRECT_URI` in Cloud Run must match exactly what is configured in Google Cloud Console →
OAuth credentials → Authorized redirect URIs. Include the trailing slash. Both the Cloud Run URL
and the custom domain need to be listed if you use both.

### Slow cold starts

Set `--min-instances=1`. Adds ~$7/month but removes the 5-10 second delay on the first morning
request:

```bash
gcloud run services update fiveaday --min-instances=1 --region=$REGION
```

### Out of memory on the testing VM

Verify the swap file is active after a reboot:

```bash
free -h   # Swap row should show ~2 GB
```

If the swap is missing, the `/etc/fstab` entry was not saved. Re-run the swap setup commands and
verify the file persists with `cat /etc/fstab`.

### Cloud Scheduler job not firing

Check job status and last execution in the GCP Console → Cloud Scheduler, or via CLI:

```bash
gcloud scheduler jobs describe JOB_NAME --location=$REGION
gcloud scheduler jobs run JOB_NAME --location=$REGION   # Manual trigger for testing
```

Ensure the service account has `roles/run.invoker` on the Cloud Run Jobs resource.
