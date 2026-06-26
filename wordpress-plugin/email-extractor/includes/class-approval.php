<?php
if (!defined('ABSPATH')) exit;

class EmailExtractor_Approval {

    public function __construct() {
        add_action('rest_api_init', [$this, 'register_routes']);
        add_action('pre_get_posts', [$this, 'allow_draft_preview']);
        add_filter('the_content', [$this, 'maybe_render_approval_banner']);
        add_action('wp_enqueue_scripts', [$this, 'enqueue_approval_assets']);
    }

    /**
     * Permite que visitantes anônimos visualizem rascunhos
     * quando o query param ?emailext_approve estiver presente e válido.
     */
    public function allow_draft_preview($query) {
        if (!is_admin() && $query->is_main_query() && !empty($_GET['emailext_approve'])) {
            $post_id = absint($_GET['p'] ?? $_GET['post_id'] ?? 0);
            if (!$post_id) return;

            $saved_token = get_post_meta($post_id, '_emailext_approval_token', true);
            if (empty($saved_token)) return;

            $token = sanitize_text_field($_GET['emailext_approve']);
            if (!hash_equals($saved_token, $token)) return;

            // Força a query a incluir rascunhos e posts futuros
            $query->set('post_status', ['draft', 'pending', 'publish', 'future']);
            // Permite acesso não-logado a este post específico
            $query->set('p', $post_id);
        }
    }

    /**
     * Registra endpoints REST para preview e aprovação.
     */
    public function register_routes() {
        register_rest_route('email-extractor/v1', '/approve', [
            'methods'             => 'POST',
            'callback'            => [$this, 'handle_approve'],
            'permission_callback' => '__return_true',
        ]);
    }

    /**
     * Renderiza o banner de aprovação no topo do conteúdo,
     * apenas se o query param ?emailext_approve=<token> estiver presente
     * e o post ainda estiver em draft.
     */
    public function maybe_render_approval_banner($content) {
        if (!is_singular('post')) return $content;

        $token = sanitize_text_field($_GET['emailext_approve'] ?? '');
        if (empty($token)) return $content;

        global $post;
        if (!$post || $post->post_status !== 'draft') return $content;

        $saved_token = get_post_meta($post->ID, '_emailext_approval_token', true);
        if (empty($saved_token) || !hash_equals($saved_token, $token)) return $content;

        $backend_url = get_option('emailext_backend_url', '');
        $site_id     = get_option('emailext_site_id', '');

        $banner = '
        <div id="emailext-approval-banner" style="
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            border: 2px solid #f59e0b;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 24px;
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif;
        ">
            <p style="margin: 0 0 12px; font-size: 16px; font-weight: 600; color: #92400e;">
                📝 Este post foi criado automaticamente e aguarda sua aprovação.
            </p>
            <button id="emailext-approve-btn" style="
                background: #059669;
                color: white;
                border: none;
                padding: 12px 32px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 2px 8px rgba(5, 150, 105, 0.3);
                transition: all 0.2s ease;
            ">
                ✅ Aprovar e Publicar
            </button>
            <p id="emailext-approve-status" style="margin: 8px 0 0; font-size: 14px; color: #92400e; display: none;"></p>
        </div>
        <script>
        (function() {
            var btn = document.getElementById("emailext-approve-btn");
            var status = document.getElementById("emailext-approve-status");
            if (!btn) return;

            btn.addEventListener("click", function() {
                btn.disabled = true;
                btn.textContent = "⏳ Publicando...";

                var data = {
                    post_id: ' . (int) $post->ID . ',
                    site_id: ' . esc_js($site_id) . ',
                    approval_token: "' . esc_js($token) . '"
                };

                fetch("' . esc_url_raw(rest_url('email-extractor/v1/approve')) . '", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(data)
                })
                .then(function(r) { return r.json(); })
                .then(function(resp) {
                    if (resp.ok) {
                        handleApprovalSuccess();
                    } else {
                        status.textContent = "❌ " + (resp.message || "Erro ao aprovar");
                        status.style.display = "block";
                        btn.disabled = false;
                        btn.textContent = "✅ Aprovar e Publicar";
                    }
                })
                .catch(function() {
                    // Se não conseguir chamar a API REST (ex: plugin desatualizado),
                    // tenta o fluxo alternativo chamando o backend diretamente.
                    fallbackApprove();
                });
            });

            function handleApprovalSuccess() {
                btn.textContent = "✅ Post publicado! Redirecionando...";
                status.textContent = "Post publicado com sucesso!";
                status.style.color = "#059669";
                status.style.display = "block";
                setTimeout(function() {
                    window.location.reload();
                }, 2000);
            }

            function fallbackApprove() {
                var backendUrl = "' . esc_url_raw($backend_url) . '";
                if (backendUrl) {
                    fetch(backendUrl + "/api/plugin/approve", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(data)
                    })
                    .then(function(r) { return r.json(); })
                    .then(function(resp) {
                        if (resp.ok) {
                            handleApprovalSuccess();
                        } else {
                            status.textContent = "❌ " + (resp.message || "Erro ao aprovar");
                            status.style.display = "block";
                            btn.disabled = false;
                            btn.textContent = "✅ Aprovar e Publicar";
                        }
                    })
                    .catch(function() {
                        status.textContent = "❌ Erro de conexão com o servidor de aprovação";
                        status.style.display = "block";
                        btn.disabled = false;
                        btn.textContent = "✅ Aprovar e Publicar";
                    });
                } else {
                    status.textContent = "❌ Erro ao aprovar. Verifique a URL do backend nas configurações do plugin.";
                    status.style.display = "block";
                    btn.disabled = false;
                    btn.textContent = "✅ Aprovar e Publicar";
                }
            }
        })();
        </script>';

        return $banner . $content;
    }

    public function enqueue_approval_assets() {
        // Assets mínimos; o banner usa inline style/script para evitar dependências externas.
    }

    /**
     * POST /wp-json/email-extractor/v1/approve
     * Altera o status do post de draft → publish e retorna OK.
     * O plugin chama o backend depois para registrar o evento.
     */
    public function handle_approve($request) {
        $params = $request->get_json_params();

        $post_id        = absint($params['post_id'] ?? 0);
        $site_id        = absint($params['site_id'] ?? 0);
        $approval_token = sanitize_text_field($params['approval_token'] ?? '');

        if (!$post_id || !$approval_token) {
            return rest_ensure_response([
                'ok'      => false,
                'message' => 'Parâmetros insuficientes: post_id e approval_token são obrigatórios.',
            ]);
        }

        $post = get_post($post_id);
        if (!$post || $post->post_type !== 'post') {
            return rest_ensure_response([
                'ok'      => false,
                'message' => 'Post não encontrado.',
            ]);
        }

        if ($post->post_status === 'publish') {
            return rest_ensure_response([
                'ok'      => true,
                'message' => 'Post já está publicado.',
            ]);
        }

        if ($post->post_status !== 'draft') {
            return rest_ensure_response([
                'ok'      => false,
                'message' => 'Post não está em rascunho. Status atual: ' . $post->post_status,
            ]);
        }

        // Valida token
        $saved_token = get_post_meta($post_id, '_emailext_approval_token', true);
        if (empty($saved_token) || !hash_equals($saved_token, $approval_token)) {
            return rest_ensure_response([
                'ok'      => false,
                'message' => 'Token de aprovação inválido.',
            ]);
        }

        // Publica o post
        $result = wp_update_post([
            'ID'          => $post_id,
            'post_status' => 'publish',
        ], true);

        if (is_wp_error($result)) {
            return rest_ensure_response([
                'ok'      => false,
                'message' => 'Erro ao publicar: ' . $result->get_error_message(),
            ]);
        }

        // Salva data de aprovação
        update_post_meta($post_id, '_emailext_approved_at', current_time('mysql'));

        // Notifica o backend sobre a aprovação (assíncrono — fire-and-forget)
        $backend_url = get_option('emailext_backend_url', '');
        if (!empty($backend_url)) {
            $notify_url = rtrim($backend_url, '/') . '/api/plugin/approve';
            wp_remote_post($notify_url, [
                'body'    => wp_json_encode([
                    'post_id'        => $post_id,
                    'site_id'        => $site_id,
                    'approval_token' => $approval_token,
                ]),
                'headers' => ['Content-Type' => 'application/json'],
                'timeout' => 10,
                'blocking' => false,
            ]);
        }

        return rest_ensure_response([
            'ok'      => true,
            'message' => 'Post publicado com sucesso!',
            'post_id' => $post_id,
            'post_url' => get_permalink($post_id),
        ]);
    }
}