#!/bin/bash
set -euo pipefail

# Configura acesso SSH à VPS para sessões do Claude Code on the web.
# Depende dos secrets do environment: VPS_SSH_KEY, VPS_HOST
# Opcionais: VPS_USER (padrão: root), VPS_PORT (padrão: 22)

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if [ -z "${VPS_SSH_KEY:-}" ] || [ -z "${VPS_HOST:-}" ]; then
  echo "VPS_SSH_KEY/VPS_HOST não configurados — pulando setup de SSH para a VPS." >&2
  exit 0
fi

mkdir -p ~/.ssh
chmod 700 ~/.ssh

printf '%s\n' "$VPS_SSH_KEY" > ~/.ssh/vps_deploy_key
chmod 600 ~/.ssh/vps_deploy_key

ssh-keyscan -H -p "${VPS_PORT:-22}" "$VPS_HOST" > ~/.ssh/vps_known_hosts 2>/dev/null || true

cat > ~/.ssh/vps_config << EOF
Host vps
  HostName $VPS_HOST
  User ${VPS_USER:-root}
  Port ${VPS_PORT:-22}
  IdentityFile ~/.ssh/vps_deploy_key
  IdentitiesOnly yes
  UserKnownHostsFile ~/.ssh/vps_known_hosts
EOF
chmod 600 ~/.ssh/vps_config

if ! grep -qF "Include ~/.ssh/vps_config" ~/.ssh/config 2>/dev/null; then
  { echo "Include ~/.ssh/vps_config"; cat ~/.ssh/config 2>/dev/null || true; } > ~/.ssh/config.tmp
  mv ~/.ssh/config.tmp ~/.ssh/config
fi
chmod 600 ~/.ssh/config

echo "SSH para VPS configurado (use: ssh vps)"
