# Запуск STROYMA на новом VPS

Инструкция для **чистого VPS с Ubuntu 24.04 LTS**, одним доменом и Docker Compose. Примерный путь проекта — `/opt/stroyma/stroyma_website`. Команды для VPS выполняются в Bash; команды переноса с текущего Windows-компьютера — в PowerShell. Замените `shop.example.ru`, `user` и `VPS_IP` своими значениями. Код с этими изменениями должен быть закоммичен и отправлен в `origin` **до** клонирования на VPS.

Сайт принимает заказы как заявки на подтверждение менеджером. Онлайн-оплаты нет. PostgreSQL и `media/` содержат рабочие данные; Git их не содержит. Для новой установки используется PostgreSQL 17, как у текущей локальной базы. **Не меняйте тег PostgreSQL на уже существующем томе `pgdata` без отдельной процедуры обновления кластера.**

## 1. Домен и VPS

Создайте A-запись `shop.example.ru → VPS_IP`. Если используете AAAA-запись, IPv6 тоже должен вести на этот VPS. На стороне провайдера откройте TCP 80/443 и свой порт SSH. Caddy получит сертификат только после корректного DNS и доступности 80/443. Для проверки с компьютера:

```powershell
nslookup shop.example.ru
ssh user@VPS_IP
```

На VPS обновите систему. Проверьте SSH-порт перед включением фаервола; ниже предполагается стандартный 22:

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl git openssl ufw
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

## 2. Docker Engine и Compose

Команды соответствуют [официальной установке Docker для Ubuntu](https://docs.docker.com/engine/install/ubuntu/). Не добавляйте обычного пользователя в группу `docker`: она даёт права уровня root. Ниже везде используется `sudo docker`.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker compose version
```

## 3. Код и секреты

```bash
sudo mkdir -p /opt/stroyma
sudo chown "$USER:$USER" /opt/stroyma
git clone https://github.com/develop-mdv/stroyma_website.git /opt/stroyma/stroyma_website
cd /opt/stroyma/stroyma_website
mkdir -p media staticfiles logs backups
umask 077
cp .env.example .env
chmod 600 .env
openssl rand -hex 48
openssl rand -hex 24
nano .env
```

Первую случайную строку поместите в `SECRET_KEY`, вторую — в `DB_PASSWORD`. В `.env` обязательно задайте:

```dotenv
SECRET_KEY=случайная_строка_из_первой_команды
DEBUG=False
ALLOWED_HOSTS=shop.example.ru
CSRF_TRUSTED_ORIGINS=https://shop.example.ru
SITE_URL=https://shop.example.ru
ADMIN_URL=admin/
DB_NAME=stroyma
DB_USER=stroyma
DB_PASSWORD=случайная_строка_из_второй_команды
EMAIL_HOST_USER=ваш_ящик@yandex.ru
EMAIL_HOST_PASSWORD=пароль_приложения_SMTP
ORDER_NOTIFY_EMAIL=ящик_для_заказов@example.ru
```

`DB_HOST` в `.env.example` может оставаться `localhost`: Compose переопределяет его на `db` для контейнеров. Для одного домена не добавляйте `www` в `ALLOWED_HOSTS`, пока не добавите его DNS и Caddy. `EMAIL_HOST_PASSWORD` — пароль приложения почтового ящика, а не пароль от панели VPS. `.env` остаётся только на сервере.

На VPS не нужны отдельные Python, PostgreSQL, Redis или Node.js: серверные зависимости устанавливаются внутри Docker-образов, а собранные CSS и шрифты уже входят в репозиторий.

Проверьте синтаксис Compose, не печатая секреты:

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
```

## 4. Данные: выберите один вариант

### Вариант А: перенести текущие товары и заказы с Windows

На **текущем компьютере**, в папке проекта, остановите локальный dev-сервер через `Ctrl+C` на время снятия дампа и копирования медиа, чтобы заказы и фотографии не менялись в процессе переноса. Значения пользователя и базы возьмите из локального `.env`:

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe' -h 127.0.0.1 -p 5432 -U ВАШ_DB_USER -d ВАШ_DB_NAME -W -F c --no-owner --no-acl -f stroyma_db.dump
tar -czf media.tgz media
scp stroyma_db.dump media.tgz user@VPS_IP:/opt/stroyma/stroyma_website/
```

`pg_dump -W` запросит пароль локальной БД. Дамп и архив медиа содержат данные клиентов; удалите временные копии с рабочей машины и VPS после проверки бэкапов. На **VPS** запустите только БД и Redis, восстановите дамп в пустую базу и распакуйте медиа:

```bash
cd /opt/stroyma/stroyma_website
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d db redis
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db sh -c 'pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < stroyma_db.dump
tar -xzf media.tgz
```

Имя базы на VPS может отличаться от локального. При переносе в пустую БД `web` затем применит недостающие миграции. Если исходная БД ещё без миграции `products.0016`, она зафиксирует для старых заказов **текущую цену товара на момент миграции**: первоначальная цена ранее не сохранялась и восстановить её автоматически нельзя.

### Вариант Б: начать с пустой базы

Ничего импортировать не требуется. Django создаст таблицы при первом запуске. Товары, категории, услуги и фотографии добавляются через админку. Для цветов/текстур фасада после запуска можно выполнить команду из шага 6.

## 5. Запуск

```bash
cd /opt/stroyma/stroyma_website
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py check --deploy
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

`web` сам выполняет `migrate` и `collectstatic`; отдельно эти команды при обычном запуске не нужны. `worker` постоянно проверяет запись уведомлений в PostgreSQL и повторяет неудачную отправку. При сбое SMTP заказ остаётся в БД, письмо будет повторено через 1, 2, 4… минуты, максимум раз в час. SMTP не даёт гарантии строго однократной доставки: при аварии непосредственно после отправки возможно повторное письмо с тем же номером заказа.

### HTTPS и сертификат

При указанном `SITE_URL=https://shop.example.ru` Caddy сам получает сертификат для этого домена, перенаправляет HTTP на HTTPS и продлевает сертификат. Устанавливать Certbot, вручную выпускать сертификат или добавлять cron для продления не нужно. Данные Caddy хранятся в постоянном томе `caddy_data`; сохраняйте его при обновлениях и не используйте `docker compose down -v`. Сертификат для `127.0.0.1` не заменяет сертификат публичного домена.

После запуска проверьте редирект, доступность HTTPS и даты сертификата **по реальному домену**:

```bash
curl -I http://shop.example.ru/
curl -I https://shop.example.ru/
curl -I https://shop.example.ru/static/css/tailwind.css
openssl s_client -connect shop.example.ru:443 -servername shop.example.ru </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 web worker nginx caddy
```

Первый `curl` должен показать переход на `https://`, второй — успешный ответ без ошибки сертификата. В выводе `openssl` проверьте домен в `subjectAltName`, издателя и поле `notAfter`. Если HTTPS не поднялся, проверьте значение `SITE_URL` в `.env`, A/AAAA-записи, открытые у провайдера и в UFW порты 80/443, `sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml ps` и журнал `caddy`. Не отключайте проверку сертификата через `curl -k`: это скроет проблему.

Проверьте вручную вход в админку, изображения товаров, оформление одного тестового заказа, уменьшение остатка и получение уведомления на `ORDER_NOTIFY_EMAIL`. Путь админки задаётся `ADMIN_URL`. До открытия сайта реальным покупателям замените шаблонные условия оферты, доставки и возврата на фактические условия вашей компании. Если пустой базе нужны цвета/текстуры конфигуратора, выполните один раз:

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py import_colors_textures
```

Команда загружает изображения по URL из `ceresit_colors_textures.json`; для неё нужен исходящий доступ к этим URL. Если письма ждут отправки, можно вызвать обработчик вручную:

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py process_order_notifications
```

В админке раздел «Уведомления о заказах» показывает число попыток, последнюю ошибку и время успешной отправки.

Очистку истёкших сессий выполняйте примерно раз в неделю, например отдельной строкой в root cron (`sudo crontab -e`):

```cron
0 4 * * 0 cd /opt/stroyma/stroyma_website && /usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T web python manage.py clear_sessions >> /var/log/stroyma-sessions.log 2>&1
```

`cleanup_media` и `optimize_media` не требуются для запуска. Сначала запускать их без `--apply` для просмотра результата; автоматический запуск с `--apply` не настраивайте.

## 6. Бэкапы и восстановление

Дамп PostgreSQL и архив `media/` создаются парой. Сделайте пробный бэкап:

```bash
cd /opt/stroyma/stroyma_website
sudo bash deploy/backup.sh
sudo ls -lh backups/
```

Запланируйте ежедневный запуск через root cron (`sudo crontab -e`), добавив строку:

```cron
0 3 * * * cd /opt/stroyma/stroyma_website && /usr/bin/bash deploy/backup.sh >> /var/log/stroyma-backup.log 2>&1
```

Выберите отдельное хранилище и копируйте туда **оба** файла бэкапа. Хранение только в `backups/` на том же VPS не защитит от потери сервера. Следите за свободным местом и сроком хранения; автоматическое удаление старых копий включайте после проверки копирования и восстановления. Отдельно сохраните `.env` и инструкции доступа в защищённом месте. Проверяйте восстановление на тестовом сервере.

Если есть **отдельный резервный сервер** с пользователем `backup`, можно настроить копирование через SSH. На резервном сервере под пользователем `backup` выполните `mkdir -m 700 -p ~/stroyma-backups`. На VPS сайта:

```bash
sudo apt-get install -y openssh-client rsync
sudo ssh-keygen -t ed25519 -f /root/.ssh/stroyma-backup -N ''
sudo ssh-copy-id -i /root/.ssh/stroyma-backup.pub backup@BACKUP_IP
sudo rsync -a -e 'ssh -i /root/.ssh/stroyma-backup' /opt/stroyma/stroyma_website/backups/ backup@BACKUP_IP:stroyma-backups/
```

После проверки доступа замените строку cron выше на следующую, чтобы копирование выполнялось сразу после успешного создания архивов:

```cron
0 3 * * * cd /opt/stroyma/stroyma_website && /usr/bin/bash deploy/backup.sh && /usr/bin/rsync -a -e 'ssh -i /root/.ssh/stroyma-backup' backups/ backup@BACKUP_IP:stroyma-backups/ >> /var/log/stroyma-backup.log 2>&1
```

Для восстановления из пары архивов **при уже работающем сайте** сначала остановите запись в БД:

```bash
cd /opt/stroyma/stroyma_website
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml stop web worker
sudo bash deploy/restore.sh backups/pg_YYYYMMDD_HHMMSS.sql.gz
sudo tar -xzf backups/media_YYYYMMDD_HHMMSS.tgz
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py check --deploy
```

Архив `media/` распаковывается поверх каталога; для точного отката на дату бэкапа восстановите его в чистый каталог, предварительно сохранив текущий. Не запускайте восстановление на рабочем сервере ради проверки — используйте отдельный тестовый VPS.

## 7. Обновление сайта

После отправки нового коммита в GitHub:

```bash
cd /opt/stroyma/stroyma_website
sudo bash deploy/backup.sh
git pull --ff-only origin master
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py check --deploy
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

При первом переходе на миграцию `products.0016` бэкап обязателен. Она фиксирует имя и цену существующих позиций по **текущему** каталогу. Не используйте `docker compose down -v`: `-v` удаляет том PostgreSQL. Для последующих обновлений образа PostgreSQL сохраняйте основную версию 17; переход на следующую основную версию требует отдельной миграции кластера.

Дополнительно: [чек-лист Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/), [автоматический HTTPS Caddy](https://caddyserver.com/docs/automatic-https), [правила совместимости дампов PostgreSQL](https://www.postgresql.org/docs/17/app-pgdump.html).
