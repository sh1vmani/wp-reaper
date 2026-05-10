FROM php:8.3-cli

ARG WPCS_VERSION=3.3.0
ARG PHPCS_VERSION=3.13.5
ARG PHPCS_PHAR_URL=https://github.com/PHPCSStandards/PHP_CodeSniffer/releases/download/${PHPCS_VERSION}/phpcs.phar
ARG PSALM_VERSION=6.16.1
ARG PSALM_PHAR_URL=https://github.com/vimeo/psalm/releases/download/${PSALM_VERSION}/psalm.phar
ARG PHPCSUTILS_VERSION=1.2.2
ARG PHPCSEXTRA_VERSION=1.5.0
ARG WP_STUBS_VERSION=v6.9.1

RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "$PHPCS_PHAR_URL" -o /usr/local/bin/phpcs \
 && chmod +x /usr/local/bin/phpcs \
 && curl -fsSL "$PSALM_PHAR_URL" -o /usr/local/bin/psalm \
 && chmod +x /usr/local/bin/psalm \
 && git clone --depth 1 --branch "$WPCS_VERSION" \
      https://github.com/WordPress/WordPress-Coding-Standards.git /opt/wpcs \
 && git clone --depth 1 --branch "$PHPCSEXTRA_VERSION" \
      https://github.com/PHPCSStandards/PHPCSExtra.git /opt/phpcsextra \
 && git clone --depth 1 --branch "$PHPCSUTILS_VERSION" \
      https://github.com/PHPCSStandards/PHPCSUtils.git /opt/phpcsutils \
 && git clone --depth 1 --branch "$WP_STUBS_VERSION" \
      https://github.com/php-stubs/wordpress-stubs.git /opt/wordpress-stubs \
 && phpcs --config-set installed_paths /opt/wpcs,/opt/phpcsextra,/opt/phpcsutils \
 && phpcs -i | grep -q WordPress

WORKDIR /app
