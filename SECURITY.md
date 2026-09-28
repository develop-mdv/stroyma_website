# Безопасность и деплой Stroyma

Краткий чек-лист для production. Кодовая часть: `django-axes` (антибрутфорс), `django-ratelimit`, CSP (`django-csp`), лимиты загрузок, списание остатков при оформлении заказа, валидация файлов в админке.

## Веб-сервер и TLS

- Разворачивайте за **nginx** или **Caddy** с **HTTPS** (Let's Encrypt, автообновление сертификатов).
- Проксируйте в Django с заголовками `X-Forwarded-Proto: https` и `Host` (уже учтено в `SECURE_PROXY_SSL_HEADER`).
- В production Compose только Caddy должен быть публичной точкой входа: он перезаписывает `X-Stroyma-Client-IP`, nginx передаёт его Django, а `TRUST_PROXY_CLIENT_IP=True` использует его для rate-limit и axes. Не публикуйте nginx или Gunicorn напрямую при этой настройке.
- В nginx: `ssl_protocols TLSv1.2 TLSv1.3`, при необходимости **limit_req** на `/accounts/login/`, `/accounts/password-reset/`, `/contact/`, `/accounts/register/`.
- Каталог `media/` считается публичным только для разрешённых изображений: nginx отклоняет остальные типы файлов и неизвестные подкаталоги. Не храните в `media/` персональные данные и резервные копии.
- Ограничьте доступ к пути админки по **IP** или вынесите `ADMIN_URL` в неочевидное значение в `.env`.

## Приложение

- `DEBUG=False`, уникальный `SECRET_KEY`, заполненные `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS` для HTTPS-домена.
- Production не запустится со слабым `SECRET_KEY` или `SECRET_KEY_FALLBACKS`; перед запуском задайте случайный ключ длиной не менее 50 символов без префикса `django-insecure-`. Не сохраняйте старый слабый ключ в fallback.
- `ORDER_NOTIFY_EMAIL` — рабочий ящик для уведомлений о заказах (по умолчанию = `EMAIL_HOST_USER`).
- Рекомендуется **Redis** для `REDIS_URL` (кеш и согласованные лимиты rate-limit / axes в multi-worker).
- Регистрация, оформление заказа и формы сообщений ограничены 15 POST/мин и 90 POST/час на IP; сброс пароля дополнительно ограничен по адресу email, повторная отправка подтверждения — по аккаунту. При распределённом спаме потребуется дополнительная защита на входном прокси или CAPTCHA. В production Compose лимиты используют общий Redis.
- Поиск ограничен 120 запросами в минуту и 600 в час на IP. Каждое действие с корзиной (добавление, обновление количества, удаление) ограничено отдельно: 60 POST/мин и 300 POST/час на IP.
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
- `python -m pip_audit -r requirements.txt` после обновления зависимостей и перед production-сборкой.
- Заголовки ответа: `Content-Security-Policy`, `Strict-Transport-Security` (при HTTPS), `X-Frame-Options`, `Referrer-Policy`.
- Сценарии: 6+ неверных логинов → блокировка (axes); повторные POST на контакт/корзину → 429 от ratelimit при превышении лимита.
