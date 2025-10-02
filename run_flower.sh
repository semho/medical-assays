#!/bin/sh

while ! nc -z rabbitmq-medical 5672; do
    echo "Ожидание RabbitMQ..."
    sleep 2
done

case "${ENV}" in
  "prod" | "dev")
    echo "Запуск Flower с префиксом"
    exec celery -A medical_mvp flower --address=0.0.0.0 --port=9999 --url-prefix=flower
    ;;
  *)
    echo "Запуск Flower без префикса"
    exec celery -A medical_mvp flower --address=0.0.0.0 --port=9999
    ;;
esac