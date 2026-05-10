#!/usr/bin/env bash
# wp-reaper toolchain installer for Kali Linux
# Host: PHP 8.x CLI + WP-CLI + Python venv.
# Container: PHPCS + Psalm + WPCS + wordpress-stubs + Semgrep.
set -euo pipefail

REPO_DIR="$(pwd)"
DOCKERFILE_DIR="$REPO_DIR/docker/tools"
TOOLS_IMAGE="wp-reaper-tools:latest"
WRAPPERS_DIR="$HOME/.local/bin"
VENV_DIR="$REPO_DIR/.venv"
WP_CLI_URL="https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar"
WP_CLI_BIN="/usr/local/bin/wp"

say()  { printf '\n[+] %s\n' "$*"; }
ok()   { printf '    verify: %s\n' "$*"; }
fail() { printf '\n[!] %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

say "Step 0: detect Kali Linux"
grep -qE '^ID=kali' /etc/os-release || fail "not Kali Linux"
ok "Kali detected"

say "Step 1: refuse to run as root"
[[ $EUID -ne 0 ]] || fail "do not run as root, run as regular user with sudo available"
ok "running as $(id -un) (uid $EUID)"

say "Step 2: apt update"
sudo apt-get update -qq
ok "apt index refreshed"

say "Step 3: PHP 8.x CLI on host (for WP-CLI)"
if ! have php || ! php -v 2>/dev/null | grep -q '^PHP 8\.'; then
  sudo apt-get install -y php-cli php-curl php-mbstring php-xml php-zip
fi
php -v | grep -q '^PHP 8\.' || fail "PHP 8.x not available"
for ext in curl mbstring xml zip; do
  php -m | grep -qi "^$ext$" || fail "PHP extension missing: $ext"
done
ok "$(php -v | head -1) with curl/mbstring/xml/zip"

say "Step 4: Docker"
have docker || fail "docker not installed -- 'sudo apt-get install docker.io' and add yourself to the docker group"
docker info >/dev/null 2>&1 || fail "docker daemon not reachable -- check service or user docker group membership"
ok "$(docker --version)"

say "Step 5: pull php:8.3-cli base image"
docker pull php:8.3-cli >/dev/null
docker image inspect php:8.3-cli >/dev/null || fail "php:8.3-cli image not present"
ok "php:8.3-cli pulled"

say "Step 6: build $TOOLS_IMAGE"
[[ -f "$DOCKERFILE_DIR/Dockerfile" ]] || fail "Dockerfile missing at $DOCKERFILE_DIR/Dockerfile"
docker build -q -t "$TOOLS_IMAGE" "$DOCKERFILE_DIR" >/dev/null
docker run --rm "$TOOLS_IMAGE" phpcs --version >/dev/null || fail "phpcs broken in image"
docker run --rm "$TOOLS_IMAGE" psalm --version >/dev/null || fail "psalm broken in image"
docker run --rm "$TOOLS_IMAGE" phpcs -i | grep -qi WordPress || fail "WordPress sniff missing in image"
docker run --rm "$TOOLS_IMAGE" test -f /opt/wordpress-stubs/wordpress-stubs.php || fail "wordpress-stubs missing in image"
ok "$TOOLS_IMAGE built and verified"

say "Step 7: install wrapper scripts to $WRAPPERS_DIR"
mkdir -p "$WRAPPERS_DIR"
mkdir -p "$HOME/.cache/wp-reaper-composer"
rm -f "$WRAPPERS_DIR/composer"  # remove stale composer wrapper from previous install
for cmd in phpcs psalm; do
  cat > "$WRAPPERS_DIR/$cmd" <<WRAPPER
#!/usr/bin/env bash
exec docker run --rm -i \\
  -v "\$PWD:/app" \\
  -v "\$HOME/.cache/wp-reaper-composer:/tmp/composer-cache" \\
  -w /app \\
  -u "\$(id -u):\$(id -g)" \\
  -e HOME=/tmp \\
  -e COMPOSER_CACHE_DIR=/tmp/composer-cache \\
  $TOOLS_IMAGE \\
  $cmd "\$@"
WRAPPER
  chmod +x "$WRAPPERS_DIR/$cmd"
done
"$WRAPPERS_DIR/phpcs" --version >/dev/null || fail "phpcs wrapper not runnable"
"$WRAPPERS_DIR/psalm" --version >/dev/null || fail "psalm wrapper not runnable"
ok "wrappers installed at $WRAPPERS_DIR/{phpcs,psalm}"

say "Step 8: WP-CLI"
if ! have wp; then
  TMP="$(mktemp)"
  curl -fsSL "$WP_CLI_URL" -o "$TMP"
  php "$TMP" --info >/dev/null || fail "downloaded WP-CLI phar broken"
  sudo install -m 0755 "$TMP" "$WP_CLI_BIN"
  rm -f "$TMP"
fi
wp --info >/dev/null || fail "wp not runnable"
ok "$(wp cli version)"

say "Step 9: Python venv at $VENV_DIR"
have python3 || sudo apt-get install -y python3 python3-venv
[[ -d "$VENV_DIR" ]] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -V >/dev/null || fail "venv python not runnable"
ok "$("$VENV_DIR/bin/python" -V)"

say "Step 10: Python packages (host)"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet --no-cache-dir requests rich typer
for pkg in requests rich typer; do
  "$VENV_DIR/bin/python" -c "import $pkg" 2>/dev/null || fail "import $pkg failed"
done
ok "requests/rich/typer installed in venv"

say "Step 11: Semgrep (containerized)"
docker pull semgrep/semgrep:latest >/dev/null
docker run --rm semgrep/semgrep:latest semgrep --version >/dev/null || fail "semgrep image broken"
cat > "$WRAPPERS_DIR/semgrep" <<'WRAPPER'
#!/usr/bin/env bash
exec docker run --rm -i \
  -v "$PWD:/src" \
  -w /src \
  -u "$(id -u):$(id -g)" \
  semgrep/semgrep:latest \
  semgrep "$@"
WRAPPER
chmod +x "$WRAPPERS_DIR/semgrep"
"$WRAPPERS_DIR/semgrep" --version >/dev/null || fail "semgrep wrapper broken"
ok "semgrep wrapper at $WRAPPERS_DIR/semgrep"

cat <<EOF

[OK] wp-reaper toolchain installed.

[INFO] Installed paths:
  php       $(command -v php)
  docker    $(command -v docker)
  wp        $(command -v wp)
  python    $VENV_DIR/bin/python
  semgrep   $WRAPPERS_DIR/semgrep      (wrapper -> semgrep/semgrep:latest)
  phpcs     $WRAPPERS_DIR/phpcs        (wrapper -> $TOOLS_IMAGE)
  psalm     $WRAPPERS_DIR/psalm        (wrapper -> $TOOLS_IMAGE)

[INFO] How to invoke:
  phpcs <args>      -- runs in container, mounts current dir as /app
  psalm <args>      -- runs in container, mounts current dir as /app
  semgrep <args>    -- runs in container, mounts current dir as /src
  wp <args>         -- runs natively on host
  python            -- activate the venv first, then use requests/rich/typer

Add this to your shell rc if not already present:
  export PATH="$WRAPPERS_DIR:\$PATH"

Activate the Python venv with:
  source $VENV_DIR/bin/activate
EOF
