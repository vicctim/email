# 📧 Email Content Extractor — TODO

> Checklist de implementação. Marque `[x]` conforme concluir cada item.  
> **Última atualização:** 2026-05-11

---

## Fase 0: Planejamento & Infra

- [x] Criar documento de planejamento (`docs/planejamento-email-extractor.md`)
- [x] Definir stack tecnológica e decisões de arquitetura
- [x] Coletar requisitos e responder perguntas abertas
- [x] Criar `docker-compose.yml` (produção)
- [x] Criar `docker-compose.local.yml` (desenvolvimento)
- [x] Criar `.env.example`
- [x] Criar `TODO.md`
- [x] Criar `.gitignore`
- [x] Inicializar repositório Git

---

## Fase 1: Backend — Setup Inicial

- [x] Criar `backend/Dockerfile` (produção)
- [x] Criar `backend/Dockerfile.dev` (dev com hot-reload)
- [x] Criar `backend/requirements.txt` com todas as dependências
- [x] Criar `backend/app/main.py` — FastAPI app com CORS e `/health`
- [x] Criar `backend/app/config.py` — Pydantic Settings (env vars)
- [x] Criar `backend/app/database/connection.py` — SQLAlchemy async engine
- [x] Criar `backend/app/database/models.py` — Modelos SQLAlchemy:
  - [x] `EmailAccount` (conta IMAP: host, user, password criptografada)
  - [x] `WordPressSite` (url, user, app_password criptografada, categorias)
  - [x] `MatchRule` (remetente, regex assunto, site destino, delay, configs)
  - [x] `PublishQueue` (email_uid, status, scheduled_at, published_at, post_id)
  - [x] `PublishLog` (histórico completo com preview do conteúdo)
- [x] Configurar Alembic para migrations
- [x] Criar migration inicial
- [x] Testar: `docker compose -f docker-compose.local.yml up postgres` sobe OK (`POSTGRES_LOCAL_PORT=5434` nesta máquina por conflito na 5433)

---

## Fase 2: IMAP Listener (Gmail)

- [x] Criar `backend/app/services/imap_listener.py`
  - [x] Conexão SSL com Gmail IMAP
  - [x] Suporte a IMAP IDLE (push notifications)
  - [x] Fallback para polling a cada 60s
  - [x] Busca apenas emails UNSEEN
  - [x] Filtro por remetente (FROM) — match contra regras do banco
  - [x] Filtro por assunto (SUBJECT) — regex match
  - [x] Decodificação de email HTML (multipart)
  - [x] Marcar email como SEEN após processamento
  - [x] Aplicar label/flag customizado (`Processed/EmailExtractor`)
- [x] Integrar listener como background task no FastAPI startup
- [ ] Teste manual: enviar email de teste e confirmar detecção

---

## Fase 3: Email Parser

- [x] Criar `backend/app/services/email_parser.py`
  - [x] Parsing do HTML com BeautifulSoup4
  - [x] Extrair título — do assunto do email (limpar prefixos)
  - [x] Extrair imagem destacada — primeira `<img>` grande (> 200px)
  - [x] Extrair excerpt — conteúdo do `<blockquote>`
  - [x] Extrair corpo — parágrafos, headings, listas, links, formatação
  - [x] Converter `<strong>`/`<b>` em parágrafo isolado → `<h3>`
  - [x] Extrair galeria — grupo de imagens no final do email
  - [x] Detectar e remover assinatura/rodapé:
    - [x] Padrão: "Todos os direitos reservados", "©", endereço
    - [x] `<table>` com layout de assinatura
    - [x] Bloco após galeria de imagens
  - [x] Retornar estrutura: `{title, excerpt, content_html, featured_image_url, gallery_image_urls[]}`
- [ ] Testes unitários com HTML de email real (fixture do ExpoQueijo)
- [ ] Teste com pelo menos 3 variações de email

---

## Fase 4: Image Handler

- [x] Criar `backend/app/services/image_handler.py`
  - [x] Download de imagens por URL (httpx async)
  - [x] Validação de tipo (JPEG, PNG, WebP)
  - [x] Redimensionamento opcional (Pillow) — max 1920px largura
  - [x] Compressão WebP opcional (qualidade configurável)
  - [x] Upload para WordPress Media Library via REST API
  - [x] Retornar `media_id` do WordPress após upload
  - [ ] Cache local temporário para evitar re-download

---

## Fase 5: WordPress Publisher

- [x] Criar `backend/app/services/wp_publisher.py`
  - [x] Autenticação via Application Password (Basic Auth)
  - [x] Upload de featured image → `POST /wp-json/wp/v2/media`
  - [x] Upload de imagens de galeria → múltiplos `POST /wp-json/wp/v2/media`
  - [x] Criação de post → `POST /wp-json/wp/v2/posts`
    - [x] `title` — do parser
    - [x] `content` — HTML parseado + shortcode de galeria
    - [x] `excerpt` — do blockquote
    - [x] `featured_media` — ID da imagem destacada
    - [x] `status: publish`
    - [x] `categories` — IDs configurados na regra
    - [x] `tags` — IDs/nomes configurados na regra
  - [x] Montar shortcode `[email_gallery ids="1,2,3"]` no conteúdo
  - [x] Verificar se post duplicado (por título ou hash do conteúdo)
  - [x] Retry com backoff exponencial (3 tentativas)
  - [x] Retornar `{post_id, post_url, status}`

---

## Fase 6: Scheduler & Task Queue (Celery)

- [x] Criar `backend/app/workers/celery_app.py` — Celery config
- [x] Criar task `process_email` — parsing + agendamento
- [x] Criar task `publish_to_wordpress` — publicação com delay
- [x] Criar task `send_whatsapp_notification` — via Evolution API
- [x] Criar task periódica `check_imap_inbox` — fallback polling
- [x] Configurar filas: `default`, `publish`, `notify`
- [x] Configurar retry policy (max 3, backoff exponencial)
- [x] Configurar Celery Beat schedule:
  - [x] `check_imap_inbox`: a cada 60s
  - [x] `cleanup_old_logs`: diário, meia-noite
- [ ] Testar: email → delay → publicação → notificação WhatsApp

---

## Fase 7: API REST (Rotas do Painel)

- [x] Criar `backend/app/api/deps.py` — dependências (DB session, auth)
- [x] Criar autenticação JWT para o painel admin
- [x] Criar rotas:
  - [x] `POST /api/auth/login` — login admin
  - [x] **Sites WordPress:**
    - [x] `GET /api/sites` — listar sites
    - [x] `POST /api/sites` — criar site
    - [x] `PUT /api/sites/{id}` — editar site
    - [x] `DELETE /api/sites/{id}` — remover site
    - [x] `POST /api/sites/{id}/test` — testar conexão WP
  - [x] **Contas de Email:**
    - [x] `GET /api/accounts` — listar contas IMAP
    - [x] `POST /api/accounts` — criar conta
    - [x] `PUT /api/accounts/{id}` — editar conta
    - [x] `DELETE /api/accounts/{id}` — remover conta
    - [x] `POST /api/accounts/{id}/test` — testar conexão IMAP
  - [x] **Regras de Matching:**
    - [x] `GET /api/rules` — listar regras
    - [x] `POST /api/rules` — criar regra
    - [x] `PUT /api/rules/{id}` — editar regra
    - [x] `DELETE /api/rules/{id}` — remover regra
    - [x] `PATCH /api/rules/{id}/toggle` — ativar/desativar
  - [x] **Fila de Publicação:**
    - [x] `GET /api/queue` — listar fila (pendentes, processando, concluídos)
    - [x] `POST /api/queue/{id}/cancel` — cancelar publicação pendente
    - [x] `POST /api/queue/{id}/retry` — re-tentar publicação falhada
    - [x] `GET /api/queue/{id}/preview` — preview do conteúdo extraído
  - [x] **Logs:**
    - [x] `GET /api/logs` — histórico com filtros (data, site, status)
    - [x] `GET /api/logs/{id}` — detalhes de um log
  - [x] **Dashboard:**
    - [x] `GET /api/dashboard/stats` — contadores (publicados, pendentes, erros)
    - [x] `GET /api/dashboard/recent` — últimos 10 posts publicados
  - [x] **Configurações:**
    - [x] `GET /api/settings` — configurações globais
    - [x] `PUT /api/settings` — atualizar configurações

---

## Fase 8: Notificações WhatsApp (Evolution API)

- [x] Criar `backend/app/services/whatsapp_notifier.py`
  - [x] Integração com Evolution API REST
  - [x] Template de mensagem: "✅ Post publicado: {titulo} → {site} — {url}"
  - [x] Template de erro: "❌ Falha ao publicar: {titulo} — {erro}"
  - [x] Enviar para número configurado
  - [x] Fallback silencioso (não bloquear publicação se WhatsApp falhar)
- [ ] Testar envio de mensagem via Evolution API

---

## Fase 9: Painel Admin (Next.js)

- [x] Inicializar projeto Next.js (`frontend/`)
- [x] Configurar estrutura de pastas e design system
- [x] Criar layout base com sidebar + header
- [x] Tela: **Login** — autenticação JWT
- [x] Tela: **Dashboard**
  - [x] Cards com contadores (publicados hoje, pendentes, erros)
  - [x] Gráfico de publicações últimos 7 dias
  - [x] Lista dos últimos posts publicados
  - [x] Status dos listeners (online/offline)
- [x] Tela: **Sites WordPress**
  - [x] Tabela com lista de sites
  - [x] Modal/drawer para criar/editar site
  - [x] Botão "Testar Conexão"
  - [x] Badge de status (conectado/erro)
- [x] Tela: **Contas de Email**
  - [x] Tabela com lista de contas IMAP
  - [x] Modal/drawer para criar/editar conta
  - [x] Botão "Testar Conexão IMAP"
  - [x] Indicador de listener ativo
- [x] Tela: **Regras de Matching**
  - [x] Tabela com regras (remetente, assunto, site destino, delay)
  - [x] Toggle ativar/desativar
  - [x] Modal/drawer para criar/editar regra
  - [x] Preview de regex match
- [x] Tela: **Fila de Publicação**
  - [x] Tabela com status (pendente, processando, publicado, erro)
  - [x] Filtros por status e data
  - [x] Ações: cancelar, re-tentar, preview
  - [x] Preview do conteúdo extraído em modal
- [x] Tela: **Logs**
  - [x] Tabela paginada com histórico
  - [x] Filtros: data, site, status
  - [x] Detalhes expandíveis
- [x] Tela: **Configurações**
  - [x] Delay global
  - [x] Intervalo de polling
  - [x] Configuração WhatsApp
  - [x] Chave secreta da API

---

## Fase 10: Plugin WordPress

- [x] Criar estrutura do plugin (`wordpress-plugin/email-extractor/`)
- [x] `email-extractor.php` — arquivo principal do plugin
- [x] `includes/class-api.php` — REST endpoint customizado
  - [x] `POST /wp-json/email-extractor/v1/publish`
  - [x] Autenticação por Bearer token
  - [x] Receber: title, content, excerpt, images, category, tags
  - [x] Criar post + upload de mídia (sideload)
  - [x] Webhook de confirmação (retorna post_id + url)
- [x] `includes/class-gallery.php` — Shortcode de galeria
  - [x] `[email_gallery ids="1,2,3" columns="3"]`
  - [x] Grid responsivo de thumbnails (1-6 colunas)
  - [x] Lightbox fullscreen (GLightbox CDN)
  - [x] Suporte a swipe no mobile
  - [x] Lazy loading das imagens
- [x] `includes/class-settings.php` — Painel no wp-admin
  - [x] Página de configurações em Settings → Email Extractor
  - [x] Campo: Token de autenticação (gerado automaticamente)
  - [x] Botões: Copiar token / Regenerar token
  - [x] Lista: últimos 20 posts recebidos
- [x] `assets/css/gallery.css` — estilos da galeria com hover/overlay
- [x] `assets/js/gallery-init.js` — GLightbox init com touch/loop
- [ ] Testar em WordPress com Classic Editor
- [ ] Testar com Elementor ativo (sem conflitos)

---

## Fase 11: Segurança

- [x] Criptografia de senhas IMAP no banco (Fernet)
- [x] Criptografia de Application Passwords do WP no banco
- [x] HTTPS obrigatório para comunicação com WordPress
- [x] Rate limiting nas rotas da API
- [ ] Validação de origem no plugin WP (HMAC ou IP whitelist)
- [x] Sanitização de HTML antes de publicar (prevenir XSS)
- [x] Logs de auditoria (quem fez o quê, quando)
- [x] `.env` no `.gitignore`

---

## Fase 12: Testes & Documentação

- [x] Testes unitários: email parser (com fixtures reais)
- [x] Testes unitários: matching rules engine
- [ ] Testes de integração: IMAP → Parser → Publisher pipeline
- [x] Testes de integração: API REST endpoints
- [ ] Teste E2E: email chega → post publicado no WP → notificação WhatsApp
- [x] Documentação: README.md principal
- [x] Documentação: Como instalar o plugin WP
- [x] Documentação: Como configurar Gmail App Password
- [x] Documentação: Como configurar Evolution API

---

## Fase 13: Deploy & Go-live

- [ ] Configurar `.env` de produção na VPS
- [ ] Criar rede `rede_publica` se não existir
- [ ] Subir stack: `docker compose up -d`
- [ ] Configurar reverse proxy (Nginx/Traefik) para backend e frontend
- [ ] Instalar plugin em pelo menos 1 site WordPress
- [ ] Cadastrar primeiro site e primeira regra no painel
- [ ] Teste end-to-end em produção
- [ ] Monitorar logs por 24h
- [ ] Instalar plugin nos demais sites (3-6)

---

## Resumo de Progresso

| Fase | Descrição | Status |
|------|-----------|--------|
| 0 | Planejamento & Infra | ✅ Concluído |
| 1 | Backend Setup | ✅ Concluído |
| 2 | IMAP Listener | 🟡 Implementado; teste manual pendente |
| 3 | Email Parser | ✅ Concluído |
| 4 | Image Handler | 🟡 Implementado; cache local opcional pendente |
| 5 | WP Publisher | ✅ Concluído |
| 6 | Scheduler (Celery) | 🟡 Implementado; E2E pendente |
| 7 | API REST | ✅ Concluído |
| 8 | WhatsApp (Evolution) | 🟡 Implementado; teste real pendente |
| 9 | Painel Admin (Next.js) | ✅ Concluído |
| 10 | Plugin WordPress | 🟡 Implementado; testes reais pendentes |
| 11 | Segurança | 🟡 Backend concluído; validação de origem no plugin pendente |
| 12 | Testes & Docs | 🟡 Parcial; E2E externo pendente |
| 13 | Deploy & Go-live | ⬜ Pendente |
