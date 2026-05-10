FROM composer:2.8

ENV COMPOSER_HOME=/composer
ENV PATH=/composer/vendor/bin:$PATH
ENV COMPOSER_ALLOW_SUPERUSER=1

RUN composer global config --no-plugins \
      allow-plugins.dealerdirect/phpcodesniffer-composer-installer true \
 && composer global require --no-interaction --no-progress \
      "squizlabs/php_codesniffer:^3.13" \
      dealerdirect/phpcodesniffer-composer-installer \
      wp-coding-standards/wpcs \
      "vimeo/psalm:^6.0" \
      php-stubs/wordpress-stubs \
 && phpcs --config-set installed_paths /composer/vendor/wp-coding-standards/wpcs \
 && phpcs -i | grep -q WordPress

WORKDIR /app
