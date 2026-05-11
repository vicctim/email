<?php
if (!defined('ABSPATH')) exit;

class EmailExtractor_Settings {

    public function __construct() {
        add_action('admin_menu', [$this, 'add_menu']);
        add_action('admin_init', [$this, 'register_settings']);
        register_activation_hook(EMAILEXT_PATH . 'email-extractor.php', [$this, 'on_activate']);
    }

    public function on_activate() {
        if (!get_option('emailext_auth_token')) {
            update_option('emailext_auth_token', wp_generate_password(48, false));
        }
    }

    public function add_menu() {
        add_options_page(
            'Email Extractor',
            'Email Extractor',
            'manage_options',
            'emailext-settings',
            [$this, 'render_page']
        );
    }

    public function register_settings() {
        register_setting('emailext_settings', 'emailext_auth_token', [
            'type' => 'string',
            'sanitize_callback' => 'sanitize_text_field',
        ]);
    }

    public function render_page() {
        $token = get_option('emailext_auth_token', '');
        $history = get_option('emailext_received_posts', []);
        $endpoint = rest_url('email-extractor/v1/publish');
        ?>
        <div class="wrap">
            <h1>⚡ Email Extractor</h1>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <!-- Config -->
                <div style="background: #fff; padding: 20px; border: 1px solid #ccd0d4; border-radius: 8px;">
                    <h2>Configuração</h2>
                    <form method="post" action="options.php">
                        <?php settings_fields('emailext_settings'); ?>

                        <table class="form-table">
                            <tr>
                                <th>Endpoint REST</th>
                                <td><code style="background: #f0f0f1; padding: 6px 10px; border-radius: 4px; font-size: 12px; word-break: break-all;"><?php echo esc_html($endpoint); ?></code></td>
                            </tr>
                            <tr>
                                <th><label for="emailext_auth_token">Token de Autenticação</label></th>
                                <td>
                                    <input type="text" id="emailext_auth_token" name="emailext_auth_token" value="<?php echo esc_attr($token); ?>" class="regular-text" style="font-family: monospace; font-size: 12px;" />
                                    <p class="description">Use este token no header: <code>Authorization: Bearer &lt;token&gt;</code></p>
                                </td>
                            </tr>
                        </table>

                        <?php submit_button('Salvar Token'); ?>
                    </form>

                    <hr />
                    <p>
                        <button type="button" class="button" onclick="navigator.clipboard.writeText('<?php echo esc_js($token); ?>').then(()=>alert('Token copiado!'))">
                            📋 Copiar Token
                        </button>
                        <button type="button" class="button" onclick="if(confirm('Gerar novo token?')){document.getElementById('emailext_auth_token').value='<?php echo esc_js(wp_generate_password(48, false)); ?>';}">
                            🔄 Regenerar Token
                        </button>
                    </p>
                </div>

                <!-- History -->
                <div style="background: #fff; padding: 20px; border: 1px solid #ccd0d4; border-radius: 8px;">
                    <h2>Últimos Posts Recebidos</h2>
                    <?php if (empty($history)): ?>
                        <p style="color: #666;">Nenhum post recebido ainda.</p>
                    <?php else: ?>
                        <table class="widefat striped" style="margin-top: 10px;">
                            <thead>
                                <tr><th>Título</th><th>Data</th><th></th></tr>
                            </thead>
                            <tbody>
                                <?php foreach (array_slice($history, 0, 10) as $item): ?>
                                    <tr>
                                        <td><?php echo esc_html($item['title']); ?></td>
                                        <td><?php echo esc_html($item['created_at']); ?></td>
                                        <td><a href="<?php echo get_edit_post_link($item['post_id']); ?>" target="_blank">Editar</a></td>
                                    </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>
                    <?php endif; ?>
                </div>
            </div>
        </div>
        <?php
    }
}
