<?php
/**
 * Plugin Name: Email Extractor Bridge
 * Plugin URI: https://github.com/vicctim/email-extractor
 * Description: Recebe posts automaticamente do sistema Email Extractor e exibe galeria com lightbox.
 * Version: 1.2.1
 * Author: Victor Samuel
 * Author URI: https://victorsamuel.com.br
 * Text Domain: email-extractor
 * Requires at least: 5.6
 * Requires PHP: 7.4
 */

if (!defined('ABSPATH')) exit;

define('EMAILEXT_VERSION', '1.2.1');
define('EMAILEXT_PATH', plugin_dir_path(__FILE__));
define('EMAILEXT_URL', plugin_dir_url(__FILE__));

require_once EMAILEXT_PATH . 'includes/class-api.php';
require_once EMAILEXT_PATH . 'includes/class-gallery.php';
require_once EMAILEXT_PATH . 'includes/class-settings.php';
require_once EMAILEXT_PATH . 'includes/class-approval.php';

class EmailExtractorPlugin {

    public function __construct() {
        new EmailExtractor_API();
        new EmailExtractor_Gallery();
        new EmailExtractor_Settings();
        new EmailExtractor_Approval();
    }
}

new EmailExtractorPlugin();
