<?php
if (!defined('ABSPATH')) exit;

class EmailExtractor_Gallery {

    public function __construct() {
        add_shortcode('email_gallery', [$this, 'render_gallery']);
        add_action('wp_enqueue_scripts', [$this, 'enqueue_assets']);
    }

    public function enqueue_assets() {
        if (!is_singular()) return;

        global $post;
        if (!$post || !has_shortcode($post->post_content, 'email_gallery')) return;

        wp_enqueue_style(
            'emailext-gallery',
            EMAILEXT_URL . 'assets/css/gallery.css',
            [],
            EMAILEXT_VERSION
        );

        wp_enqueue_style(
            'glightbox-css',
            'https://cdn.jsdelivr.net/npm/glightbox@3.3.0/dist/css/glightbox.min.css',
            [],
            '3.3.0'
        );

        wp_enqueue_script(
            'glightbox-js',
            'https://cdn.jsdelivr.net/npm/glightbox@3.3.0/dist/js/glightbox.min.js',
            [],
            '3.3.0',
            true
        );

        wp_enqueue_script(
            'emailext-gallery-js',
            EMAILEXT_URL . 'assets/js/gallery-init.js',
            ['glightbox-js'],
            EMAILEXT_VERSION,
            true
        );
    }

    public function render_gallery($atts) {
        $atts = shortcode_atts([
            'ids'     => '',
            'columns' => 3,
            'size'    => 'medium',
        ], $atts, 'email_gallery');

        if (empty($atts['ids'])) return '';

        $ids = array_map('intval', explode(',', $atts['ids']));
        $columns = max(1, min(6, intval($atts['columns'])));

        $output = '<div class="emailext-gallery" style="--columns: ' . $columns . ';">';

        foreach ($ids as $id) {
            $full_url = wp_get_attachment_image_url($id, 'full');
            $thumb_url = wp_get_attachment_image_url($id, $atts['size']);
            $alt = get_post_meta($id, '_wp_attachment_image_alt', true);
            $caption = wp_get_attachment_caption($id);

            if (!$full_url) continue;

            $output .= '<a href="' . esc_url($full_url) . '" class="glightbox emailext-gallery-item" data-gallery="emailext"';
            if ($caption) $output .= ' data-title="' . esc_attr($caption) . '"';
            $output .= '>';
            $output .= '<img src="' . esc_url($thumb_url ?: $full_url) . '" alt="' . esc_attr($alt) . '" loading="lazy" />';
            $output .= '<div class="emailext-gallery-overlay"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg></div>';
            $output .= '</a>';
        }

        $output .= '</div>';

        return $output;
    }
}
