# Email Content Extractor

Ferramenta para monitorar caixas Gmail via IMAP, extrair conteúdo estruturado de releases/newsletters e publicar automaticamente em sites WordPress pela REST API. O projeto inclui backend FastAPI, painel Next.js e plugin WordPress para endpoint/galeria.

## Arquitetura

- `backend/`: API FastAPI, listener IMAP, parser HTML, fila Celery, publicação WordPress, notificações WhatsApp e auditoria.
- `frontend/`: painel administrativo para sites, contas de email, regras, fila, logs e configurações.
- `wordpress-plugin/email-extractor/`: plugin WP com endpoint customizado e shortcode de galeria.
- Infra local/prod: PostgreSQL, Redis, backend, workers Celery, Celery Beat e frontend via Docker Compose.

## Gmail App Password

1. Ative a verificação em duas etapas na conta Google.
2. Acesse `https://myaccount.google.com/apppasswords`.
3. Gere uma senha de app para uso em e-mail/IMAP.
4. No painel, cadastre a conta com host `imap.gmail.com`, porta `993`, SSL ativo e a App Password gerada.
5. Mantenha as regras de remetente e assunto restritas, especialmente por ser uma caixa pessoal.

## Evolution API

Configure no `.env`:

```env
EVOLUTION_API_URL=https://evolutionapi.victorsamuel.com.br
EVOLUTION_API_KEY=sua-api-key
EVOLUTION_INSTANCE=emailext
WHATSAPP_NOTIFY_NUMBER=5534999999999
```

O backend envia mensagens de sucesso e erro sem bloquear a publicação caso a API esteja indisponível.

## Plugin WordPress

1. Envie a pasta `wordpress-plugin/email-extractor/` para `wp-content/plugins/`.
2. Ative o plugin no wp-admin.
3. Configure o token no painel do plugin, quando usar o endpoint customizado.
4. Para galeria no Classic Editor, o backend adiciona o shortcode `[email_gallery ids="1,2,3"]`.
5. Confirme que Application Passwords estão habilitadas no WordPress para publicação via REST API padrão.

## Rodar Local

```bash
cp .env.example .env
docker compose -f docker-compose.local.yml up -d
```

Se a porta `5433` já estiver ocupada:

```bash
POSTGRES_LOCAL_PORT=5434 docker compose -f docker-compose.local.yml up -d
```

Depois, aplique migrations no backend:

```bash
docker compose -f docker-compose.local.yml run --rm backend alembic upgrade head
```

## Testes

```bash
cd backend
TEST_DATABASE_URL=postgresql+asyncpg://emailext:emailext_dev_123@127.0.0.1:5434/emailext pytest
```

Os testes desabilitam listener IMAP e rate limiting por ambiente.

## Deploy Produção

1. Preencha `.env` com `APP_SECRET_KEY`, credenciais PostgreSQL, Evolution API e `NEXT_PUBLIC_API_URL`.
2. Garanta que a rede externa `rede_publica` exista.
3. Suba a stack:

```bash
docker compose up -d
```

4. Rode migrations:

```bash
docker compose run --rm backend alembic upgrade head
```

5. Configure reverse proxy HTTPS para backend e frontend.
6. Instale o plugin WordPress nos sites, cadastre sites/contas/regras no painel e execute um teste end-to-end.

