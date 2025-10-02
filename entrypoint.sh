#!/bin/sh

# Убеждаемся, что зависимости установлены
uv sync --frozen

while ! nc -z postgres-medical 5432; do
  >&2 echo "PostgreSQL недоступен - ожидание..."
  sleep 2
done

# Очищаем директорию с метриками при старте
#rm -rf /opt/prometheus/*

# Создаем директории
mkdir -p /app/temp_uploads /app/media

python manage.py showmigrations
python manage.py migrate --noinput

# Собираем статические файлы
echo "Сбор статических файлов..."
python manage.py collectstatic --noinput

echo "Starting development server on http://${HOST:-0.0.0.0}:8000"
exec python manage.py runserver 0.0.0.0:8000


