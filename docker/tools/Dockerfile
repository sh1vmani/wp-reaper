FROM php:8.3-cli

ARG WPCS_VERSION=3.3.0
ARG PHPCS_PHAR_URL=https://github.com/squizlabs/PHP_CodeSniffer/releases/latest/download/phpcs.phar
ARG PSALM_PHAR_URL=https://github.com/vimeo/psalm/releases/latest/download/psalm.phar

RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "$PHPCS_PHAR_URL" -o /usr/local/bin/phpcs \
 && chmod +x /usr/local/bin/phpcs \
 && curl -fsSL "$PSALM_PHAR_URL" -o /usr/local/bin/psalm \
 && chmod +x /usr/local/bin/psalm \
 && git clone --depth 1 --branch "$WPCS_VERSION" \
      https://github.com/WordPress/WordPress-Coding-Standards.git /opt/wpcs \
 && git clone --depth 1 \
      https://github.com/PHPCSStandards/PHPCSExtra.git /opt/phpcsextra \
 && git clone --depth 1 \
      https://github.com/PHPCSStandards/PHPCSUtils.git /opt/phpcsutils \
 && git clone --depth 1 \
      https://github.com/php-stubs/wordpress-stubs.git /opt/wordpress-stubs \
 && phpcs --config-set installed_paths /opt/wpcs,/opt/phpcsextra,/opt/phpcsutils \
 && phpcs -i | grep -q WordPress

WORKDIR /app
