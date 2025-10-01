#!/bin/sh

while ! nc -z postgres-medical 5432; do
  >&2 echo "PostgreSQL недоступен - ожидание..."
  sleep 2
done

# Очищаем директорию с метриками при старте
#rm -rf /opt/prometheus/*

# Создаем директории
mkdir -p /app/temp_uploads /app/media

uv run manage.py showmigrations
uv run manage.py migrate --noinput

# Собираем статические файлы
echo "Сбор статических файлов..."
uv run manage.py collectstatic --noinput

echo "Running in local mode http://${HOST}"
exec uv run manage.py runserver 0.0.0.0:8000


