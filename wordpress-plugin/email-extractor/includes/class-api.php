<?php
if (!defined('ABSPATH')) exit;

class EmailExtractor_API {

    public function __construct() {
        add_action('rest_api_init', [$this, 'register_routes']);
    }

    public function register_routes() {
        register_rest_route('email-extractor/v1', '/publish', [
            'methods'             => 'POST',
            'callback'            => [$this, 'handle_publish'],
            'permission_callback' => [$this, 'check_auth'],
        ]);

        register_rest_route('email-extractor/v1', '/status', [
            'methods'             => 'GET',
            'callback'            => [$this, 'handle_status'],
            'permission_callback' => [$this, 'check_auth'],
        ]);
    }

    public function check_auth($request) {
        $token = get_option('emailext_auth_token', '');
        if (empty($token)) return false;

        $header = $request->get_header('Authorization');
        if (!$header) return false;

        $parts = explode(' ', $header);
        if (count($parts) !== 2 || strtolower($parts[0]) !== 'bearer') return false;

        return hash_equals($token, $parts[1]);
    }

    public function handle_status() {
        return rest_ensure_response([
            'status'  => 'ok',
            'plugin'  => 'email-extractor',
            'version' => EMAILEXT_VERSION,
            'site'    => get_bloginfo('name'),
            'url'     => home_url(),
        ]);
    }

    public function handle_publish($request) {
        $params = $request->get_json_params();

        $title   = sanitize_text_field($params['title'] ?? '');
        $content = wp_kses_post($params['content'] ?? '');
        $excerpt = sanitize_textarea_field($params['excerpt'] ?? '');
        $status  = sanitize_text_field($params['status'] ?? 'publish');

        if (empty($title) || empty($content)) {
            return new WP_Error('missing_data', 'Title and content are required', ['status' => 400]);
        }

        // Upload featured image
        $featured_media_id = 0;
        $featured_url = $params['featured_image_url'] ?? '';
        if (!empty($featured_url)) {
            $featured_media_id = $this->sideload_image($featured_url, $title);
        }

        // Upload gallery images
        $gallery_ids = [];
        $gallery_urls = $params['gallery_images'] ?? [];
        foreach ($gallery_urls as $img_url) {
            $media_id = $this->sideload_image($img_url, $title . ' - gallery');
            if ($media_id && !is_wp_error($media_id)) {
                $gallery_ids[] = $media_id;
            }
        }

        // Append gallery shortcode if images exist
        if (!empty($gallery_ids)) {
            $ids_str = implode(',', $gallery_ids);
            $content .= "\n\n[email_gallery ids=\"{$ids_str}\" columns=\"3\"]";
        }

        // Resolve category
        $category_name = $params['category'] ?? '';
        $category_ids = [];
        if (!empty($category_name)) {
            $term = get_term_by('name', $category_name, 'category');
            if ($term) {
                $category_ids[] = $term->term_id;
            } else {
                $new_term = wp_insert_term($category_name, 'category');
                if (!is_wp_error($new_term)) {
                    $category_ids[] = $new_term['term_id'];
                }
            }
        }

        // Resolve tags
        $tag_names = $params['tags'] ?? [];

        // Create post
        $post_data = [
            'post_title'    => $title,
            'post_content'  => $content,
            'post_excerpt'  => $excerpt,
            'post_status'   => in_array($status, ['publish', 'draft', 'pending']) ? $status : 'publish',
            'post_type'     => 'post',
            'post_author'   => 1,
            'post_category' => $category_ids,
            'tags_input'    => $tag_names,
        ];

        $post_id = wp_insert_post($post_data, true);

        if (is_wp_error($post_id)) {
            return new WP_Error('insert_failed', $post_id->get_error_message(), ['status' => 500]);
        }

        // Set featured image
        if ($featured_media_id && !is_wp_error($featured_media_id)) {
            set_post_thumbnail($post_id, $featured_media_id);
        }

        // Save metadata
        update_post_meta($post_id, '_emailext_source', 'email-extractor');
        update_post_meta($post_id, '_emailext_gallery_ids', $gallery_ids);

        // Track last received
        $history = get_option('emailext_received_posts', []);
        array_unshift($history, [
            'post_id'    => $post_id,
            'title'      => $title,
            'created_at' => current_time('mysql'),
        ]);
        update_option('emailext_received_posts', array_slice($history, 0, 20));

        return rest_ensure_response([
            'status'  => 'ok',
            'post_id' => $post_id,
            'post_url' => get_permalink($post_id),
            'featured_media_id' => $featured_media_id,
            'gallery_ids' => $gallery_ids,
        ]);
    }

    private function sideload_image($url, $description = '') {
        require_once ABSPATH . 'wp-admin/includes/media.php';
        require_once ABSPATH . 'wp-admin/includes/file.php';
        require_once ABSPATH . 'wp-admin/includes/image.php';

        $tmp = download_url($url, 30);
        if (is_wp_error($tmp)) return $tmp;

        $filename = basename(parse_url($url, PHP_URL_PATH));
        if (empty($filename)) $filename = 'image-' . time() . '.jpg';

        $file_array = [
            'name'     => sanitize_file_name($filename),
            'tmp_name' => $tmp,
        ];

        $id = media_handle_sideload($file_array, 0, $description);

        if (is_wp_error($id)) {
            @unlink($tmp);
        }

        return $id;
    }
}
