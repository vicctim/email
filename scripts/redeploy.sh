#!/usr/bin/env bash
# Redeploy do projeto email — chamado pelo GitHub Actions após push na main.
set -euo pipefail

DEPLOY_DIR="/srv/clientes/victor/email"
cd "$DEPLOY_DIR"

echo "[redeploy] Pull do repositório..."
git pull origin main

echo "[redeploy] Build das imagens..."
docker compose build backend celery_worker frontend

echo "[redeploy] Subindo containers atualizados..."
docker compose up -d

echo "[redeploy] Aguardando backend ficar healthy..."
timeout 60 bash -c 'until docker inspect emailext_backend --format "{{.State.Health.Status}}" 2>/dev/null | grep -q healthy; do sleep 2; done'

echo "[redeploy] Executando migrations..."
docker compose exec -T backend alembic upgrade head

echo "[redeploy] Concluído."
docker compose ps --format "table {{.Name}}\t{{.Status}}"
