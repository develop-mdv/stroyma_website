# Перенос PostgreSQL с хост-машины в контейнер Docker

Однократная процедура, когда база уже есть на `localhost`, а сайт переезжает на VPS с `docker compose`.

## 1. Дамп с текущего сервера (Windows / Linux с локальным Postgres)

Установите переменные окружения или используйте учётные данные из вашего `.env`:

```powershell
$env:PGPASSWORD = "ваш_пароль"
pg_dump -h localhost -p 5432 -U ваш_пользователь -d ваша_база `
  --no-owner --no-acl --clean --if-exists `
  -F c -f stroyma_db.dump
```

Формат `-F c` (custom) удобен для `pg_restore`.

## 2. Копирование на VPS

Скопируйте `stroyma_db.dump` и репозиторий проекта на сервер.

## 3. Запуск только PostgreSQL в Compose

В каталоге проекта:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d db
```

Убедитесь, что в `.env` те же `DB_NAME`, `DB_USER`, `DB_PASSWORD`, что подставляются в `docker-compose.yml` для сервиса `db`.

## 4. Восстановление в контейнер

```bash
docker cp stroyma_db.dump "$(docker compose -f docker-compose.yml -f docker-compose.prod.yml ps -q db):/tmp/"
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/stroyma_db.dump'
```

Если база в контейнере пустая и имя БД совпадает с `POSTGRES_DB`, перед этим можно не создавать БД вручную — образ Postgres создаёт её при первом старте.

## 5. Запуск всего стека

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Проверка:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py shell -c "from products.models import FacadeColor; print(FacadeColor.objects.count())"
```

## Медиа-файлы

Каталог `media/` монтируется с хоста (`./media:/app/media`). Скопируйте его на VPS целиком, если материалы уже загружены.
