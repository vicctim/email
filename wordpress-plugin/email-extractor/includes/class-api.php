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

        register_rest_route('email-extractor/v1', '/categories', [
            'methods'             => 'GET',
            'callback'            => [$this, 'handle_categories'],
            'permission_callback' => [$this, 'check_auth'],
        ]);

        register_rest_route('email-extractor/v1', '/authors', [
            'methods'             => 'GET',
            'callback'            => [$this, 'handle_authors'],
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

    public function handle_categories() {
        $terms = get_terms([
            'taxonomy'   => 'category',
            'hide_empty' => false,
            'orderby'    => 'name',
            'order'      => 'ASC',
        ]);

        if (is_wp_error($terms)) {
            return new WP_Error('categories_failed', $terms->get_error_message(), ['status' => 500]);
        }

        $categories = array_map(function ($term) {
            return [
                'id'    => (int) $term->term_id,
                'name'  => $term->name,
                'slug'  => $term->slug,
                'count' => (int) $term->count,
            ];
        }, $terms);

        return rest_ensure_response(['categories' => $categories]);
    }

    public function handle_authors() {
        $users = get_users([
            'orderby' => 'display_name',
            'order'   => 'ASC',
        ]);

        $authors = [];
        foreach ($users as $user) {
            if (!user_can($user->ID, 'edit_posts')) {
                continue;
            }

            $authors[] = [
                'id'       => (int) $user->ID,
                'name'     => $user->display_name ?: $user->user_login,
                'username' => $user->user_login,
            ];
        }

        return rest_ensure_response(['authors' => $authors]);
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

        $category_ids = [];
        $raw_category_ids = $params['categories'] ?? ($params['category_ids'] ?? []);
        if (!is_array($raw_category_ids)) {
            $raw_category_ids = [$raw_category_ids];
        }

        foreach ($raw_category_ids as $category_id) {
            $category_id = absint($category_id);
            if ($category_id && term_exists($category_id, 'category')) {
                $category_ids[] = $category_id;
            }
        }

        // Backward compatibility: older integrations may send a category name.
        $category_name = sanitize_text_field($params['category'] ?? '');
        if (empty($category_ids) && !empty($category_name)) {
            $term = get_term_by('name', $category_name, 'category');
            if ($term) {
                $category_ids[] = (int) $term->term_id;
            } else {
                $new_term = wp_insert_term($category_name, 'category');
                if (!is_wp_error($new_term)) {
                    $category_ids[] = (int) $new_term['term_id'];
                }
            }
        }

        $category_ids = array_values(array_unique($category_ids));

        // Resolve tags
        $tag_names = $params['tags'] ?? [];
        $author_id = $this->resolve_author_id($params);
        if (is_wp_error($author_id)) {
            return $author_id;
        }

        // Create post
        $post_data = [
            'post_title'    => $title,
            'post_content'  => $content,
            'post_excerpt'  => $excerpt,
            'post_status'   => in_array($status, ['publish', 'draft', 'pending']) ? $status : 'publish',
            'post_type'     => 'post',
            'post_author'   => $author_id,
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

        // Salva token de aprovação se enviado (aprovação manual)
        $approval_token = sanitize_text_field($params['approval_token'] ?? '');
        if (!empty($approval_token)) {
            update_post_meta($post_id, '_emailext_approval_token', $approval_token);
        }

        // Salva URL do backend e ID do site
        $backend_url_param = sanitize_text_field($params['_backend_url'] ?? '');
        if (!empty($backend_url_param)) {
            update_option('emailext_backend_url', esc_url_raw($backend_url_param));
        }
        $site_id_param = absint($params['_site_id'] ?? 0);
        if ($site_id_param) {
            update_option('emailext_site_id', $site_id_param);
        }

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

    private function resolve_author_id($params) {
        $raw_author_id = absint($params['author_id'] ?? ($params['author'] ?? 0));
        if ($raw_author_id) {
            return user_can($raw_author_id, 'edit_posts')
                ? $raw_author_id
                : new WP_Error('invalid_author', 'Autor informado não pode publicar posts', ['status' => 400]);
        }

        $author_username = sanitize_user($params['author_username'] ?? '');
        if (!empty($author_username)) {
            $user = get_user_by('login', $author_username);
            if (!$user) {
                return new WP_Error('invalid_author', 'Autor informado não existe', ['status' => 400]);
            }
            if (!user_can($user->ID, 'edit_posts')) {
                return new WP_Error('invalid_author', 'Autor informado não pode publicar posts', ['status' => 400]);
            }
            return (int) $user->ID;
        }

        return 1;
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
