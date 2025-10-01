#!/bin/bash

# Ждем, пока RabbitMQ станет доступен
while ! nc -z rabbitmq-medical 5672; do
    echo "Ожидание доступности RabbitMQ..."
    sleep 2
done

# Определяем наличие URL-префикса в зависимости от окружения
case "${ENV}" in
  "prod" | "dev")
    echo "Запуск Flower в режиме разработки/продакшн с префиксом."
    exec uv run celery -A medical_mvp flower --address=0.0.0.0 --port=9999 --url-prefix=flower
    ;;
  *)
    echo "Запуск Flower в локальном режиме без префикса."
    exec uv run celery -A medical_mvp flower --address=0.0.0.0 --port=9999
    ;;
esac