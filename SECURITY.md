# Безопасность и деплой Stroyma

Краткий чек-лист для production. Кодовая часть: `django-axes` (антибрутфорс), `django-ratelimit`, CSP (`django-csp`), лимиты загрузок, списание остатков при оформлении заказа, валидация файлов в админке.

## Веб-сервер и TLS

- Разворачивайте за **nginx** или **Caddy** с **HTTPS** (Let's Encrypt, автообновление сертификатов).
- Проксируйте в Django с заголовками `X-Forwarded-Proto: https` и `Host` (уже учтено в `SECURE_PROXY_SSL_HEADER`).
- В nginx: `ssl_protocols TLSv1.2 TLSv1.3`, при необходимости **limit_req** на `/accounts/login/`, `/accounts/password-reset/`, `/contact/`, `/accounts/register/`.
- Ограничьте доступ к пути админки по **IP** или вынесите `ADMIN_URL` в неочевидное значение в `.env`.

## Приложение

- `DEBUG=False`, уникальный `SECRET_KEY`, заполненные `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS` для HTTPS-домена.
- `ORDER_NOTIFY_EMAIL` — рабочий ящик для уведомлений о заказах (по умолчанию = `EMAIL_HOST_USER`).
- Рекомендуется **Redis** для `REDIS_URL` (кеш и согласованные лимиты rate-limit / axes в multi-worker).
- Суперпользователь: сильный пароль, по возможности **2FA** на почте/SSH сервера.

## База и бэкапы

- PostgreSQL: отдельный пользователь с минимальными правами, в `pg_hba` без `trust` для внешних сетей.
- Регулярные **pg_dump** и копия каталога **media/** (cron + хранение 14+ дней, off-site).

## Сеть и боты

- **fail2ban** (или аналог) по логам nginx на множество 4xx/401 с одного IP.
- Фаервол: открыты только 22/80/443 (SSH по ключу).

## Мониторинг

- Uptime, алерты по 5xx. Опционально Sentry для исключений в Python.
- Проверка логов: `logs/errors.log`, `logs/app.log` на диске проекта (см. `LOGGING` в `settings.py`).

## Проверка после выката

- `python manage.py check --deploy` с production-like `.env`.
- Заголовки ответа: `Content-Security-Policy`, `Strict-Transport-Security` (при HTTPS), `X-Frame-Options`, `Referrer-Policy`.
- Сценарии: 6+ неверных логинов → блокировка (axes); повторные POST на контакт/корзину → 403 от ratelimit при превышении лимита.
