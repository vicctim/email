# Plano: Correção de Bugs + Feature de Aprovação Manual

---

## Parte 1 — 🐛 Bugs e Melhorias Imediatas

### Bug 1: Tags enviadas como IDs em vez de nomes (via REST API pura)

**Problema**: Em `wp_publisher.py:101`, tags são enviadas como `rule.tag_ids` (ints) — no plugin isso funciona (`tags_input` aceita nomes), mas via REST API pura (`_publish_with_wordpress_rest`, linha 168) o WordPress REST espera **nomes** para o campo `tags`. Tags com IDs numéricos criarão tags inválidas.

**Correção**: No fluxo sem plugin, converter IDs para nomes via `GET /wp-json/wp/v2/tags`. Melhor: armazenar nomes no model em vez de IDs.

**Arquivo**: `backend/app/services/wp_publisher.py`

### Bug 2: UID duplicado não é marcado como lido

**Problema**: Se o IMAP listener enfileira um email que já existe na `publish_queue`, a task retorna e o email **não é marcado como lido nem processado**. No próximo ciclo ele reprocessa eternamente.

**Correção**: No IMAP listener, após encontrar match de regra, verificar se `(account_id, email_uid)` já existe na queue. Se sim, marcar como lido e ignorar.

**Arquivos**: `backend/app/services/imap_listener.py` (adicionar consulta assíncrona) ou marcar na task `process_email` e retornar flag pro listener marcar.

### Bug 3: Memory leak no rate limiter fallback

**Problema**: `_memory_is_allowed` usa `defaultdict(deque)` sem limite de tamanho. Se muitos requests passarem com Redis fora, a memória cresce indefinidamente.

**Correção**: Logar warning e retornar `(True, 60)` (permitir tudo) quando Redis falha, em vez de fallback em memória.

**Arquivo**: `backend/app/api/rate_limit.py`

---

## Parte 2 — 🏗️ Feature: Aprovação Manual

### Conceito

Quando ativado por site (check "Exige aprovação manual"):

1. **Publicação como draft** — mesmo com `post_status = "publish"`, post vai como `draft`
2. **Geração de token** único por post
3. **Notificação WhatsApp** — "📝 Post aguardando aprovação: {título} — {link}/?emailext_approve=TOKEN"
4. **Link com preview** — acessa o post com banner de aprovação no topo
5. **Banner de aprovação** — plugin exibe: botão "✅ Aprovar e Publicar"
6. **Pós-aprovação** — plugin chama webhook no backend → post muda `draft → publish` + notifica sucesso via WhatsApp

### O que muda em cada arquivo

| Arquivo | Mudança |
|---------|---------|
| `models.py` | + `WordPressSite.approval_required: bool`; + `PublishQueue.needs_approval`, + `PublishQueue.approval_token`, + `PublishQueue.approved_at` |
| `schemas.py` | + `approval_required` no site create/update/read |
| `sites.py` | propagar campo |
| `migrations/` | nova migration com campos |
| `wp_publisher.py` | se `approval_required`, forçar `status=draft` e gerar `approval_token` |
| `tasks.py` | notificação diferenciada: "📝 Post aguardando aprovação" ao invés de "✅ Post publicado" |
| `plugin.py` (backend) | + `POST /api/plugin/approve` — webhook que o plugin chama quando aprovado |
| `class-api.php` (plugin) | + POST /approve endpoint (muda draft → publish) |
| `class-approval.php` (novo) | banner de aprovação renderizado no the_content |
| `email-extractor.php` | + require class-approval.php |
| `sites/page.tsx` | checkbox "Exige aprovação manual" |
| Settings do plugin WP | + campo "Backend URL" para webhook callback |
| `whatsapp_notifier.py` | + método `send_approval_pending` |

### Design do Banner

- Fundo: gradiente amarelo-dourado
- Texto: "📝 Este post foi criado automaticamente e aguarda sua aprovação"
- Botão: "✅ Aprovar e Publicar" (estilo verde)
- Apenas visível com `?emailext_approve=<token>`
- Se o post já estiver publicado ou token inválido: não exibe ou exibe "Este post já foi aprovado"

### Fluxo de Dados

```
Email chega → IMAP detecta → Task process_email
→ wp_publisher detecta approval_required=true
→ Publica como draft, gera approval_token
→ Salva token no queue_item.extra_data
→ task notificação WA: envia link com token
→ Cliente acessa link → plugin renderiza banner
→ Cliente clica "Aprovar" → plugin muda status publish
→ Plugin faz POST pro backend confirmar
→ Backend atualiza queue_item.status = published
→ Backend envia WA: "✅ Post aprovado e publicado"
```

---

## Perguntas pra você

1. **O banner fica visível no site público ou só com o link especial?**
   - Sugiro: só quem tem o link (query param `?emailext_approve=TOKEN`)

2. **Expiração do token?**
   - Sugiro: 7 dias. Após expirar, post permanece draft.

3. **Precisa de login pra aprovar?**
   - Sugiro: não. Só o link + token. Cliente final clica e aprova sem cadastro.

4. **Plugin precisa saber URL do backend pra chamar webhook.**
   - Vou adicionar campo "Backend URL" no settings do plugin WordPress.