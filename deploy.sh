#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Email Content Extractor
# Autor: Victor Samuel
# Uso:   bash deploy.sh
#
# O que este script faz:
#   1. Verifica dependências (docker, git, openssl)
#   2. Clona o repositório na estrutura correta (/srv/clientes/victor/email)
#   3. Gera automaticamente todas as chaves/senhas seguras
#   4. Solicita apenas os dados que NÃO podem ser gerados (Gmail, WhatsApp, etc.)
#   5. Cria a rede Docker pública (rede_publica)
#   6. Faz o build e sobe toda a stack
#   7. Executa as migrations do banco
#   8. Exibe o status final
# =============================================================================

set -euo pipefail

# ─── Cores ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log()     { echo -e "${GREEN}✔${RESET}  $*"; }
info()    { echo -e "${BLUE}ℹ${RESET}  $*"; }
warn()    { echo -e "${YELLOW}⚠${RESET}  $*"; }
error()   { echo -e "${RED}✖${RESET}  $*" >&2; }
section() { echo -e "\n${BOLD}${CYAN}══ $* ══${RESET}\n"; }

# ─── Config ───────────────────────────────────────────────────────────────────
REPO_URL="git@github.com:vicctim/email.git"
DEPLOY_DIR="/srv/clientes/victor/email"
ENV_FILE="${DEPLOY_DIR}/.env"

# ─── 1. Verificar dependências ────────────────────────────────────────────────
section "Verificando dependências"

for cmd in docker git openssl curl; do
  if command -v "$cmd" &>/dev/null; then
    log "$cmd encontrado"
  else
    error "$cmd não encontrado. Instale antes de continuar."
    exit 1
  fi
done

# Docker Compose v2
if docker compose version &>/dev/null; then
  log "docker compose v2 encontrado"
else
  error "docker compose v2 não encontrado. Atualize o Docker."
  exit 1
fi

# ─── 2. Verificar SSH para GitHub ─────────────────────────────────────────────
section "Verificando acesso SSH ao GitHub"

if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
  log "Chave SSH autenticada no GitHub"
else
  warn "Não foi possível autenticar no GitHub via SSH."
  echo ""
  echo "  Gere uma chave SSH e adicione ao GitHub:"
  echo "  ${CYAN}ssh-keygen -t ed25519 -C 'vps@deploy'${RESET}"
  echo "  ${CYAN}cat ~/.ssh/id_ed25519.pub${RESET}  → cole em github.com/settings/keys"
  echo ""
  read -r -p "Pressione ENTER após adicionar a chave, ou CTRL+C para cancelar..."
fi

# ─── 3. Clonar ou atualizar repositório ───────────────────────────────────────
section "Repositório"

mkdir -p "$(dirname "$DEPLOY_DIR")"

if [ -d "$DEPLOY_DIR/.git" ]; then
  info "Repositório já existe. Atualizando..."
  git -C "$DEPLOY_DIR" pull --ff-only
  log "Repositório atualizado"
else
  info "Clonando $REPO_URL → $DEPLOY_DIR"
  git clone "$REPO_URL" "$DEPLOY_DIR"
  log "Repositório clonado"
fi

cd "$DEPLOY_DIR"

# ─── 4. Coletar dados que precisam de input humano ────────────────────────────
section "Configuração — dados obrigatórios"

echo -e "Preencha os dados abaixo. ${YELLOW}Deixe em branco para usar o padrão entre [ ]${RESET}\n"

prompt_required() {
  local var_name="$1"
  local prompt_text="$2"
  local value=""
  while [ -z "$value" ]; do
    read -r -p "  ${BOLD}${prompt_text}${RESET}: " value
    [ -z "$value" ] && echo "  ${RED}Este campo é obrigatório.${RESET}"
  done
  echo "$value"
}

prompt_optional() {
  local prompt_text="$1"
  local default="$2"
  local value=""
  read -r -p "  ${BOLD}${prompt_text}${RESET} [${default}]: " value
  echo "${value:-$default}"
}

# Gmail
GMAIL_USER=$(prompt_required "GMAIL_USER" "Gmail usado para leitura IMAP (ex: seu@gmail.com)")
GMAIL_APP_PASSWORD=$(prompt_required "GMAIL_APP_PASSWORD" "App Password do Gmail (16 chars, sem espaços)")

# WhatsApp
WHATSAPP_NOTIFY_NUMBER=$(prompt_optional "Número WhatsApp para notificações (ex: 5511999999999)" "")
EVOLUTION_API_KEY=$(prompt_optional "Evolution API Key" "")
EVOLUTION_INSTANCE=$(prompt_optional "Evolution API Instance" "emailext")

# Admin
ADMIN_USERNAME=$(prompt_optional "Username do painel admin" "admin")

# Domínios
BACKEND_DOMAIN=$(prompt_optional "Domínio da API backend (ex: emailext-api.victorsamuel.com.br)" "emailext-api.victorsamuel.com.br")
FRONTEND_DOMAIN=$(prompt_optional "Domínio do painel frontend (ex: emailext.victorsamuel.com.br)" "emailext.victorsamuel.com.br")

# ─── 5. Gerar senhas e chaves automaticamente ─────────────────────────────────
section "Gerando chaves e senhas seguras"

gen_secret()   { openssl rand -hex 32; }
gen_password() { openssl rand -base64 18 | tr -d '/+=' | head -c 24; }

APP_SECRET_KEY=$(gen_secret)
POSTGRES_PASSWORD=$(gen_password)
ADMIN_PASSWORD=$(gen_password)

log "APP_SECRET_KEY   gerado (64 chars hex)"
log "POSTGRES_PASSWORD gerado (24 chars)"
log "ADMIN_PASSWORD    gerado (24 chars)"

# ─── 6. Escrever o .env ───────────────────────────────────────────────────────
section "Criando .env de produção"

if [ -f "$ENV_FILE" ]; then
  BACKUP="${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
  warn ".env já existe → backup em ${BACKUP}"
  cp "$ENV_FILE" "$BACKUP"
fi

cat > "$ENV_FILE" <<EOF
# ============================================================
# Email Content Extractor — .env de produção
# Gerado por deploy.sh em $(date -u '+%Y-%m-%d %H:%M:%S UTC')
# ============================================================

# ─── App ─────────────────────────────────────────────────────
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=${APP_SECRET_KEY}

# ─── PostgreSQL ───────────────────────────────────────────────
POSTGRES_USER=emailext
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=emailext

# ─── Redis ────────────────────────────────────────────────────
# (Sem senha — isolado na rede interna emailext_net)

# ─── Gmail IMAP ───────────────────────────────────────────────
GMAIL_USER=${GMAIL_USER}
GMAIL_APP_PASSWORD=${GMAIL_APP_PASSWORD}
IMAP_LISTENER_ENABLED=true

# ─── Admin Panel ──────────────────────────────────────────────
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# ─── WhatsApp (Evolution API) ─────────────────────────────────
EVOLUTION_API_URL=https://evolutionapi.victorsamuel.com.br
EVOLUTION_API_KEY=${EVOLUTION_API_KEY}
EVOLUTION_INSTANCE=${EVOLUTION_INSTANCE}
WHATSAPP_NOTIFY_NUMBER=${WHATSAPP_NOTIFY_NUMBER}

# ─── Domínios / CORS ──────────────────────────────────────────
NEXT_PUBLIC_API_URL=https://${BACKEND_DOMAIN}
CORS_ORIGINS=["https://${FRONTEND_DOMAIN}"]

# ─── Comportamento ────────────────────────────────────────────
DEFAULT_PUBLISH_DELAY=10
SETTINGS_STORAGE_PATH=media/settings.json
EOF

chmod 600 "$ENV_FILE"
log ".env criado com permissão 600 (somente root/owner)"

# ─── 7. Rede Docker ───────────────────────────────────────────────────────────
section "Rede Docker"

if docker network ls --format '{{.Name}}' | grep -q '^rede_publica$'; then
  log "rede_publica já existe"
else
  docker network create rede_publica
  log "rede_publica criada"
fi

# ─── 8. Build e subir a stack ─────────────────────────────────────────────────
section "Build e inicialização da stack"

info "Fazendo build das imagens (pode demorar alguns minutos)..."
docker compose build --no-cache

info "Subindo os serviços..."
docker compose up -d

# ─── 9. Aguardar banco ficar saudável ─────────────────────────────────────────
section "Aguardando PostgreSQL ficar pronto"

MAX_WAIT=60
WAITED=0
until docker compose exec -T postgres pg_isready -U emailext -d emailext &>/dev/null; do
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    error "PostgreSQL não ficou pronto em ${MAX_WAIT}s. Verifique: docker compose logs postgres"
    exit 1
  fi
  echo -n "."
  sleep 2
  WAITED=$((WAITED + 2))
done
echo ""
log "PostgreSQL pronto"

# ─── 10. Executar migrations ──────────────────────────────────────────────────
section "Executando migrations (Alembic)"

docker compose exec -T backend alembic upgrade head
log "Migrations aplicadas"

# ─── 11. Status final ─────────────────────────────────────────────────────────
section "Status da stack"

docker compose ps

echo ""
echo -e "${BOLD}${GREEN}════════════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}  Deploy concluído com sucesso! 🚀${RESET}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Painel Admin:${RESET}  https://${FRONTEND_DOMAIN}"
echo -e "  ${BOLD}API Backend:${RESET}   https://${BACKEND_DOMAIN}/docs"
echo ""
echo -e "  ${BOLD}Credenciais do painel:${RESET}"
echo -e "  Usuário:  ${CYAN}${ADMIN_USERNAME}${RESET}"
echo -e "  Senha:    ${CYAN}${ADMIN_PASSWORD}${RESET}"
echo ""
echo -e "  ${YELLOW}⚠  Guarde a senha acima! Ela não será exibida novamente.${RESET}"
echo -e "  ${YELLOW}⚠  Certifique-se de configurar o reverse proxy (Nginx/Traefik)${RESET}"
echo -e "     ${YELLOW}apontando para os containers:${RESET}"
echo -e "     Backend:  ${CYAN}emailext_backend:8000${RESET}"
echo -e "     Frontend: ${CYAN}emailext_frontend:3000${RESET}"
echo ""
EOF
