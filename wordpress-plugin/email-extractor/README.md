# Email Extractor Bridge — Plugin WordPress

Plugin que conecta seu site WordPress ao sistema **Email Extractor**, recebendo posts automaticamente via API REST e exibindo galerias de imagens com lightbox fullscreen.

## Instalação

1. Copie a pasta `email-extractor/` para `wp-content/plugins/`
2. Ative o plugin no painel WordPress → Plugins
3. Vá em **Configurações → Email Extractor**
4. Copie o **Token de Autenticação** gerado automaticamente
5. No painel do Email Extractor, cadastre o site usando esse token

## Funcionalidades

### API REST

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/wp-json/email-extractor/v1/publish` | POST | Recebe e publica post com imagens |
| `/wp-json/email-extractor/v1/status` | GET | Verifica conexão e status do plugin |

**Autenticação:** `Authorization: Bearer <token>`

### Galeria com Lightbox

Shortcode: `[email_gallery ids="1,2,3" columns="3"]`

- Grid responsivo (1-6 colunas)
- Hover com zoom e overlay
- Clique abre **GLightbox** em tela cheia
- Suporte a swipe no mobile
- Lazy loading

### Painel Admin

Em **Configurações → Email Extractor**:
- Token de autenticação (copiar/regenerar)
- Endpoint REST visível
- Histórico dos últimos 20 posts recebidos

## Requisitos

- WordPress 5.6+
- PHP 7.4+
- REST API habilitada
