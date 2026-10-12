#!/usr/bin/env bash
# Deploy su Cloud Run + Cloud Scheduler in un comando.
# Prerequisiti: gcloud CLI installato e autenticato (gcloud auth login).
# Compila le variabili sotto (o esportale), poi: bash deploy.sh
set -euo pipefail

# ====== COMPILA ======
PROJECT_ID="${PROJECT_ID:-}"                     # il tuo progetto GCP
REGION="${REGION:-europe-west8}"                 # Milano
SERVICE="${SERVICE:-task-assistant}"
SCHEDULER_REGION="${SCHEDULER_REGION:-$REGION}"

export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
export GROQ_API_KEY="${GROQ_API_KEY:-}"
export GITHUB_TOKEN="${GITHUB_TOKEN:-}"
export GITHUB_REPO="${GITHUB_REPO:-}"            # owner/repo
export GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
# =====================

export TELEGRAM_SECRET="${TELEGRAM_SECRET:-$(openssl rand -hex 16)}"
export SCHEDULER_SECRET="${SCHEDULER_SECRET:-$(openssl rand -hex 16)}"

for v in PROJECT_ID TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID GROQ_API_KEY GITHUB_TOKEN GITHUB_REPO; do
  [ -n "${!v}" ] || { echo "Manca $v"; exit 1; }
done

gcloud config set project "$PROJECT_ID"

echo "1/6 Abilito le API..."
gcloud services enable run.googleapis.com cloudscheduler.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com

# Cloud Build (--source) usa il compute default SA: senza run.builder la build fallisce
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role roles/run.builder --condition=None >/dev/null \
  || echo "   ATTENZIONE: binding roles/run.builder fallito"

echo "2/6 Preparo le env e faccio il deploy su Cloud Run..."
ENVFILE="$(mktemp)"
cat > "$ENVFILE" <<EOF
TELEGRAM_BOT_TOKEN: "${TELEGRAM_BOT_TOKEN}"
TELEGRAM_CHAT_ID: "${TELEGRAM_CHAT_ID}"
TELEGRAM_SECRET: "${TELEGRAM_SECRET}"
GROQ_API_KEY: "${GROQ_API_KEY}"
GITHUB_TOKEN: "${GITHUB_TOKEN}"
GITHUB_REPO: "${GITHUB_REPO}"
GITHUB_BRANCH: "${GITHUB_BRANCH}"
SCHEDULER_SECRET: "${SCHEDULER_SECRET}"
TZ: "Europe/Rome"
EOF
gcloud run deploy "$SERVICE" --source . --region "$REGION" \
  --allow-unauthenticated --env-vars-file "$ENVFILE"
rm -f "$ENVFILE"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)')"
echo "   URL: $URL"

echo "3/6 Creo/aggiorno i job scheduler (8:00 e 19:00 Europe/Rome)..."
for h in 8 19; do
  JOB="recap-$h"
  if gcloud scheduler jobs describe "$JOB" --location "$SCHEDULER_REGION" >/dev/null 2>&1; then
    CMD=update; HDR=--update-headers
  else
    CMD=create; HDR=--headers
  fi
  gcloud scheduler jobs $CMD http "$JOB" --location "$SCHEDULER_REGION" \
    --schedule "0 $h * * *" --time-zone "Europe/Rome" \
    --uri "$URL/recap" --http-method POST \
    $HDR "X-Scheduler-Secret=${SCHEDULER_SECRET}"
done

echo "4/6 Registro il webhook Telegram..."
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  --data-urlencode "url=${URL}/telegram" \
  --data-urlencode "secret_token=${TELEGRAM_SECRET}" | grep -q '"ok":true' \
  && echo "   webhook ok" || echo "   ATTENZIONE: webhook non impostato"

echo "5/6 Inizializzo tasks.md nel repo (se assente)..."
API="https://api.github.com/repos/${GITHUB_REPO}/contents/tasks/tasks.md"
GH=(-H "Authorization: Bearer ${GITHUB_TOKEN}" -H "User-Agent: setup" -H "Accept: application/vnd.github+json")
CODE="$(curl -s -o /dev/null -w '%{http_code}' "${GH[@]}" "${API}?ref=${GITHUB_BRANCH}")"
case "$CODE" in
  200) echo "   tasks.md esiste già" ;;
  404)
    CONTENT="$(printf -- '- [MEDIA] Esempio task — rimuovimi\n' | base64 | tr -d '\n')"
    RESP="$(mktemp)"
    PUT="$(curl -s -o "$RESP" -w '%{http_code}' -X PUT "${GH[@]}" "$API" \
      -d "{\"message\":\"init tasks\",\"content\":\"${CONTENT}\",\"branch\":\"${GITHUB_BRANCH}\"}")"
    [ "$PUT" = 201 ] && echo "   creato tasks/tasks.md" \
      || { echo "   ERRORE GitHub PUT $PUT (token senza Contents:write? repo/branch inesistente?)"; cat "$RESP"; }
    rm -f "$RESP" ;;
  *) echo "   ERRORE GitHub GET $CODE: token non valido o senza accesso a $GITHUB_REPO" ;;
esac

echo "6/6 FATTO."
echo "Service URL     : $URL"
echo "SCHEDULER_SECRET: $SCHEDULER_SECRET   (serve per outlook_reader.py)"
