#!/usr/bin/env bash
# wp-reaper toolchain installer for Kali Linux
set -euo pipefail

COMPOSER_BIN_DIR="$HOME/.config/composer/vendor/bin"
COMPOSER_VENDOR_DIR="$HOME/.config/composer/vendor"
VENV_DIR="$(pwd)/.venv"
WP_CLI_URL="https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar"
WP_CLI_BIN="/usr/local/bin/wp"

say()  { printf '\n[+] %s\n' "$*"; }
ok()   { printf '    verify: %s\n' "$*"; }
fail() { printf '\n[!] %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

export PATH="$COMPOSER_BIN_DIR:$PATH"

say "Step 0: detect Kali Linux"
grep -qE '^ID=kali' /etc/os-release || fail "not Kali Linux"
ok "Kali detected"

say "Step 1: refuse to run as root"
[[ $EUID -ne 0 ]] || fail "do not run as root, run as regular user with sudo available"
ok "running as $(id -un) (uid $EUID)"

say "Step 2: apt update"
sudo apt-get update -qq
ok "apt index refreshed"

say "Step 3: PHP 8.x CLI + extensions"
if ! have php || ! php -v 2>/dev/null | grep -q '^PHP 8\.'; then
  sudo apt-get install -y php-cli php-curl php-mbstring php-xml php-zip
fi
php -v | grep -q '^PHP 8\.' || fail "PHP 8.x not available"
for ext in curl mbstring xml zip; do
  php -m | grep -qi "^$ext$" || fail "PHP extension missing: $ext"
done
ok "$(php -v | head -1) with curl/mbstring/xml/zip"

say "Step 4: Composer"
have composer || sudo apt-get install -y composer
composer --version >/dev/null || fail "composer not runnable"
ok "$(composer --version)"

say "Step 5: packagist reachability"
curl -fsSL --max-time 5 https://repo.packagist.org/packages.json -o /dev/null || fail "cannot reach packagist.org"
ok "packagist.org reachable"

say "Step 6: PHP_CodeSniffer (global)"
composer global require --quiet --no-interaction "squizlabs/php_codesniffer:^3.13"
have phpcs || fail "phpcs not on PATH ($COMPOSER_BIN_DIR)"
ok "$(phpcs --version)"

say "Step 7: WordPress-Coding-Standards"
composer global config --no-plugins allow-plugins.dealerdirect/phpcodesniffer-composer-installer true
composer global require --quiet --no-interaction \
  dealerdirect/phpcodesniffer-composer-installer \
  wp-coding-standards/wpcs
phpcs --config-set installed_paths "$COMPOSER_VENDOR_DIR/wp-coding-standards/wpcs" >/dev/null
phpcs -i | grep -qi 'WordPress' || fail "WordPress sniff not registered"
ok "phpcs -i lists WordPress"

say "Step 8: Psalm (global)"
composer global require --quiet --no-interaction vimeo/psalm
have psalm || fail "psalm not on PATH"
ok "$(psalm --version | head -1)"

say "Step 9: php-stubs/wordpress-stubs"
composer global require --quiet --no-interaction php-stubs/wordpress-stubs
STUBS="$COMPOSER_VENDOR_DIR/php-stubs/wordpress-stubs/wordpress-stubs.php"
[[ -f "$STUBS" ]] || fail "wordpress-stubs file missing: $STUBS"
ok "stubs at $STUBS"

say "Step 10: WP-CLI"
if ! have wp; then
  TMP="$(mktemp)"
  curl -fsSL "$WP_CLI_URL" -o "$TMP"
  php "$TMP" --info >/dev/null || fail "downloaded WP-CLI phar broken"
  sudo install -m 0755 "$TMP" "$WP_CLI_BIN"
  rm -f "$TMP"
fi
wp --info >/dev/null || fail "wp not runnable"
ok "$(wp cli version)"

say "Step 11: Python venv at $VENV_DIR"
have python3 || sudo apt-get install -y python3 python3-venv
[[ -d "$VENV_DIR" ]] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -V >/dev/null || fail "venv python not runnable"
ok "$("$VENV_DIR/bin/python" -V)"

say "Step 12: Python packages"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet semgrep requests rich typer
"$VENV_DIR/bin/semgrep" --version >/dev/null || fail "semgrep not runnable"
for pkg in requests rich typer; do
  "$VENV_DIR/bin/python" -c "import $pkg" 2>/dev/null || fail "import $pkg failed"
done
ok "semgrep $("$VENV_DIR/bin/semgrep" --version) + requests/rich/typer"

cat <<EOF

[OK] wp-reaper toolchain installed.

[INFO] Installed paths:
  php       $(command -v php)
  composer  $(command -v composer)
  phpcs     $(command -v phpcs)
  psalm     $(command -v psalm)
  wp        $(command -v wp)
  python    $VENV_DIR/bin/python
  semgrep   $VENV_DIR/bin/semgrep
  stubs     $STUBS

Add this to your shell rc if not already present:
  export PATH="$COMPOSER_BIN_DIR:\$PATH"

Activate the Python venv with:
  source $VENV_DIR/bin/activate
EOF
