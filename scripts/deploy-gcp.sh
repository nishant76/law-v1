#!/usr/bin/env bash
# SuperAdvocate — Full GCP deployment script
# Run this once after: gcloud auth login
#
# Usage:
#   ./scripts/deploy-gcp.sh
#
# Set GCP_PROJECT_ID env var to override the default project name:
#   GCP_PROJECT_ID=my-project ./scripts/deploy-gcp.sh
#
# Secrets are read from your local .env file on first run.
# Set SKIP_SECRETS=1 to skip secret creation (if already done).

set -euo pipefail
cd "$(dirname "$0")/.."   # run from repo root

# ── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step()    { echo -e "\n${BOLD}${CYAN}━━━ $* ━━━${NC}"; }

# ── Config ─────────────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-superadvocate-prod}"
REGION="asia-south1"
REPO="superadvocate"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"
BACKEND_SERVICE="superadvocate-backend"
FRONTEND_SERVICE="superadvocate-frontend"

echo -e "\n${BOLD}SuperAdvocate → GCP Deployment${NC}"
echo "  Project:  ${PROJECT_ID}"
echo "  Region:   ${REGION}"
echo "  Registry: ${REGISTRY}"

# ── Preflight checks ───────────────────────────────────────────────────────
step "Preflight"

command -v gcloud >/dev/null 2>&1 || error "gcloud not found. Install: brew install --cask google-cloud-sdk"
command -v docker  >/dev/null 2>&1 || error "docker not found. Install Docker Desktop."

# Verify gcloud auth
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  error "Not authenticated. Run: gcloud auth login"
fi
success "Authenticated as ${ACTIVE_ACCOUNT}"

# Verify Docker is running
docker info >/dev/null 2>&1 || error "Docker daemon is not running. Start Docker Desktop."
success "Docker is running"

# Check local backend image exists
docker image inspect law-v1-backend:latest >/dev/null 2>&1 || {
  warn "Backend image not found locally. Building now..."
  docker build --platform linux/amd64 -t law-v1-backend:latest .
}
success "Backend image ready"

# ── GCP Project ────────────────────────────────────────────────────────────
step "GCP Project"

if gcloud projects describe "${PROJECT_ID}" >/dev/null 2>&1; then
  success "Project ${PROJECT_ID} exists"
else
  info "Creating project ${PROJECT_ID}..."
  gcloud projects create "${PROJECT_ID}" --name="SuperAdvocate" || {
    warn "Could not create project. It may already exist or the ID is taken."
    warn "Set GCP_PROJECT_ID=<another-id> and re-run."
    exit 1
  }
  success "Project created"

  echo ""
  echo -e "${YELLOW}Action required:${NC}"
  echo "  1. Open https://console.cloud.google.com/billing/linkedaccount?project=${PROJECT_ID}"
  echo "  2. Link a billing account (Cloud Run requires billing to be enabled)"
  echo ""
  read -rp "Press Enter once billing is linked... " _
fi

gcloud config set project "${PROJECT_ID}" --quiet
success "Project set to ${PROJECT_ID}"

# ── Enable APIs ────────────────────────────────────────────────────────────
step "Enable APIs"
info "Enabling required APIs (this takes ~60 seconds on first run)..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com \
  --quiet
success "APIs enabled"

# ── Artifact Registry ──────────────────────────────────────────────────────
step "Artifact Registry"
if gcloud artifacts repositories describe "${REPO}" \
     --location="${REGION}" >/dev/null 2>&1; then
  success "Registry already exists"
else
  info "Creating Artifact Registry repository..."
  gcloud artifacts repositories create "${REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="SuperAdvocate Docker images" \
    --quiet
  success "Registry created"
fi

info "Configuring Docker credentials for registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
success "Docker auth configured"

# ── Secret Manager ─────────────────────────────────────────────────────────
step "Secret Manager"

if [[ "${SKIP_SECRETS:-0}" != "1" ]]; then
  # Load values from .env
  if [[ ! -f .env ]]; then
    error ".env file not found. Cannot read secret values."
  fi

  load_env_var() {
    local key="$1"
    grep -E "^${key}=" .env | cut -d= -f2- | tr -d '"' | tr -d "'"
  }

  create_or_update_secret() {
    local name="$1"
    local value="$2"
    if [[ -z "$value" || "$value" == *"<"* ]]; then
      warn "Skipping ${name} — value is empty or a placeholder"
      return
    fi
    if gcloud secrets describe "${name}" >/dev/null 2>&1; then
      echo -n "${value}" | gcloud secrets versions add "${name}" --data-file=- --quiet
      info "Updated secret: ${name}"
    else
      echo -n "${value}" | gcloud secrets create "${name}" --data-file=- --quiet
      info "Created secret: ${name}"
    fi
  }

  OPENAI_API_KEY_VAL=$(load_env_var "OPENAI_API_KEY")
  DATABASE_URL_VAL=$(load_env_var "DATABASE_URL")
  ECOURTS_API_TOKEN_VAL=$(load_env_var "ECOURTS_API_TOKEN")

  # JWT secret — generate a strong one if it's still the dev placeholder
  JWT_SECRET_VAL=$(load_env_var "JWT_SECRET_KEY")
  if [[ "$JWT_SECRET_VAL" == "dev-secret-key-change-in-production" || -z "$JWT_SECRET_VAL" ]]; then
    JWT_SECRET_VAL=$(openssl rand -base64 48)
    warn "Generated new JWT secret (dev placeholder detected)"
  fi

  # Redis — will be set after Upstash is configured
  REDIS_URL_VAL=$(load_env_var "REDIS_URL")
  if [[ "$REDIS_URL_VAL" == "redis://localhost:6379/0" ]]; then
    warn "REDIS_URL is still localhost. Skipping — set it after creating Upstash Redis."
    warn "Run: echo -n 'rediss://...' | gcloud secrets create REDIS_URL --data-file=- --project=${PROJECT_ID}"
    REDIS_URL_VAL=""
  fi

  create_or_update_secret "OPENAI_API_KEY"     "$OPENAI_API_KEY_VAL"
  create_or_update_secret "DATABASE_URL"       "$DATABASE_URL_VAL"
  create_or_update_secret "JWT_SECRET_KEY"     "$JWT_SECRET_VAL"
  create_or_update_secret "ECOURTS_API_TOKEN"  "$ECOURTS_API_TOKEN_VAL"
  if [[ -n "$REDIS_URL_VAL" ]]; then
    create_or_update_secret "REDIS_URL"        "$REDIS_URL_VAL"
  fi

  success "Secrets stored in Secret Manager"
else
  info "Skipping secret creation (SKIP_SECRETS=1)"
fi

# Grant Cloud Run service account access to read secrets
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
info "Granting secret access to ${SA_EMAIL}..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet >/dev/null
success "Secret access granted"

# Check all required secrets are present
MISSING_SECRETS=()
for secret in OPENAI_API_KEY DATABASE_URL JWT_SECRET_KEY REDIS_URL ECOURTS_API_TOKEN; do
  if ! gcloud secrets describe "$secret" >/dev/null 2>&1; then
    MISSING_SECRETS+=("$secret")
  fi
done
if [[ ${#MISSING_SECRETS[@]} -gt 0 ]]; then
  warn "Missing secrets: ${MISSING_SECRETS[*]}"
  warn "Backend will deploy but may fail health check until these are set."
fi

# ── Push backend image ─────────────────────────────────────────────────────
step "Backend Image → Artifact Registry"
BACKEND_IMAGE="${REGISTRY}/backend:latest"

info "Tagging backend image..."
docker tag law-v1-backend:latest "${BACKEND_IMAGE}"

info "Pushing to Artifact Registry (this may take a few minutes)..."
docker push "${BACKEND_IMAGE}"
success "Backend image pushed: ${BACKEND_IMAGE}"

# ── Deploy backend ─────────────────────────────────────────────────────────
step "Deploy Backend → Cloud Run"

# Build set-secrets arg — skip missing ones
SECRETS_ARG=""
for secret in OPENAI_API_KEY DATABASE_URL JWT_SECRET_KEY ECOURTS_API_TOKEN; do
  if gcloud secrets describe "$secret" >/dev/null 2>&1; then
    SECRETS_ARG="${SECRETS_ARG}${secret}=${secret}:latest,"
  fi
done
if gcloud secrets describe "REDIS_URL" >/dev/null 2>&1; then
  SECRETS_ARG="${SECRETS_ARG}REDIS_URL=REDIS_URL:latest,"
fi
SECRETS_ARG="${SECRETS_ARG%,}"  # trim trailing comma

DEPLOY_CMD=(
  gcloud run deploy "${BACKEND_SERVICE}"
  --image "${BACKEND_IMAGE}"
  --region "${REGION}"
  --platform managed
  --allow-unauthenticated
  --port 8000
  --memory 1Gi
  --cpu 1
  --min-instances 0
  --max-instances 10
  --timeout 300
  --set-env-vars "ENVIRONMENT=production,USE_AZURE_OPENAI=false"
  --quiet
)
if [[ -n "$SECRETS_ARG" ]]; then
  DEPLOY_CMD+=(--set-secrets "$SECRETS_ARG")
fi

info "Deploying backend..."
"${DEPLOY_CMD[@]}"

BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
  --region "${REGION}" \
  --format "value(status.url)")
success "Backend deployed: ${BACKEND_URL}"

# Quick health check
info "Health check..."
sleep 3
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/api/v1/health" 2>/dev/null || echo "000")
if [[ "$HTTP_STATUS" == "200" ]]; then
  success "Health check passed (HTTP 200)"
elif [[ "$HTTP_STATUS" == "503" ]]; then
  warn "Health check returned 503 — some services may not be configured yet (e.g. Redis)"
else
  warn "Health check returned HTTP ${HTTP_STATUS} — check logs:"
  warn "  gcloud run logs read --service=${BACKEND_SERVICE} --region=${REGION}"
fi

# ── Build & push frontend ──────────────────────────────────────────────────
step "Frontend Image → Artifact Registry"
FRONTEND_IMAGE="${REGISTRY}/frontend:latest"

info "Building frontend with VITE_API_URL=${BACKEND_URL}"
info "(This takes ~2-3 minutes — bun install + vite build)"

docker buildx build \
  --platform linux/amd64 \
  --build-arg "VITE_API_URL=${BACKEND_URL}" \
  -t "${FRONTEND_IMAGE}" \
  frontends/law-v2/

info "Pushing frontend image..."
docker push "${FRONTEND_IMAGE}"
success "Frontend image pushed: ${FRONTEND_IMAGE}"

# ── Deploy frontend ────────────────────────────────────────────────────────
step "Deploy Frontend → Cloud Run"

gcloud run deploy "${FRONTEND_SERVICE}" \
  --image "${FRONTEND_IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --quiet

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
  --region "${REGION}" \
  --format "value(status.url)")
success "Frontend deployed: ${FRONTEND_URL}"

# ── Wire FRONTEND_URL into backend ─────────────────────────────────────────
step "Update CORS"
info "Adding frontend URL to backend CORS config..."
gcloud run services update "${BACKEND_SERVICE}" \
  --region "${REGION}" \
  --update-env-vars "FRONTEND_URL=${FRONTEND_URL}" \
  --quiet
success "CORS updated — backend now allows ${FRONTEND_URL}"

# ── GitHub Actions service account ─────────────────────────────────────────
step "GitHub Actions Service Account (CI/CD)"

SA_NAME="github-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="/tmp/gcp-sa-key.json"

if gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
  info "Service account already exists: ${SA_EMAIL}"
else
  info "Creating service account for GitHub Actions..."
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="GitHub Actions Deployer" \
    --quiet

  for role in roles/run.admin roles/artifactregistry.writer roles/iam.serviceAccountUser roles/secretmanager.secretAccessor; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role="${role}" \
      --quiet >/dev/null
  done
  success "Service account created"
fi

info "Exporting service account key → ${KEY_FILE}"
gcloud iam service-accounts keys create "${KEY_FILE}" \
  --iam-account="${SA_EMAIL}" \
  --quiet
success "Key saved to ${KEY_FILE}"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}━━━ Deployment Complete ━━━${NC}"
echo ""
echo "  Frontend:  ${FRONTEND_URL}"
echo "  Backend:   ${BACKEND_URL}"
echo "  Health:    ${BACKEND_URL}/api/v1/health"
echo ""
echo -e "${BOLD}Next steps:${NC}"
echo ""

if [[ ${#MISSING_SECRETS[@]} -gt 0 ]]; then
  echo -e "  ${YELLOW}1. Set missing secrets:${NC} ${MISSING_SECRETS[*]}"
  echo "     gcloud secrets create SECRET_NAME --data-file=- --project=${PROJECT_ID}"
  echo ""
fi

echo "  2. Add GCP_SA_KEY to GitHub Secrets:"
echo "     - Go to your GitHub repo → Settings → Secrets and variables → Actions"
echo "     - New repository secret: name=GCP_SA_KEY, value=contents of ${KEY_FILE}"
echo "     - Delete the key file: rm ${KEY_FILE}"
echo ""
echo "  3. Set FRONTEND_URL in GitHub Variables (for CI):"
echo "     - Go to GitHub repo → Settings → Secrets → Variables"
echo "     - New variable: FRONTEND_URL=${FRONTEND_URL}"
echo ""
echo "  4. (Optional) Custom domain:"
echo "     gcloud run domain-mappings create --service ${FRONTEND_SERVICE} --domain app.superadvocate.ai --region ${REGION}"
echo "     gcloud run domain-mappings create --service ${BACKEND_SERVICE} --domain api.superadvocate.ai --region ${REGION}"
echo ""
