# Medical MVP - Медицинский Анализатор

Безопасная платформа для автоматизированного анализа медицинских результатов с максимальной защитой персональных данных.

## 🚀 Ключевые особенности

- **Безопасность "Process & Delete"**: Файлы удаляются через 60 секунд после обработки
- **End-to-end шифрование**: Индивидуальные AES-256 ключи для каждого пользователя
- **OCR распознавание**: Автоматическое извлечение данных из PDF и изображений
- **Анализ динамики**: Отслеживание изменений показателей во времени
- **Мультиязычность**: Поддержка русского и английского языков
- **Полнофункциональный API**: REST API для интеграции с внешними системами
- **Асинхронная обработка**: Celery для обработки файлов в фоновом режиме

## 📋 Поддерживаемые типы анализов

- Общий анализ крови (ОАК)
- Биохимический анализ крови
- Гормональные анализы
- Прочие медицинские показатели

## 🛠 Технологический стек

### Backend
- **Framework**: Django 5.2 + Django REST Framework
- **Database**: PostgreSQL 15.4
- **Cache/Queue**: Redis 7
- **Message Broker**: RabbitMQ 3.13
- **Async Processing**: Celery + Celery Beat
- **OCR**: Tesseract + PyMuPDF
- **Security**: AES-256 шифрование, индивидуальные ключи
- **Monitoring**: Flower для мониторинга Celery

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Web Server**: Nginx
- **Package Manager**: uv (modern Python package manager)
- **Python**: 3.13+

## 🏗 Архитектура безопасности

```
┌─────────────┐
│ Пользователь│
└──────┬──────┘
       │ Загрузка файла (PDF/изображение)
       ↓
┌──────────────────────────────────────┐
│   Временное хранение (60 секунд)     │
│   /temp_uploads/{session_id}/        │
└──────┬───────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────┐
│     OCR + Парсинг (Celery Worker)    │
│   Tesseract → PyMuPDF → Структура    │
└──────┬───────────────────────────────┘
       │
       ↓
┌──────────────────────────────────────┐
│    Шифрование данных (AES-256)       │
│  Индивидуальный ключ пользователя    │
└──────┬───────────────────────────────┘
       │
       ├─────────────────────────────────┐
       │                                 │
       ↓                                 ↓
┌─────────────────┐          ┌──────────────────┐
│ Сохранение в БД │          │ Удаление файла   │
│ (зашифровано)   │          │ (автоматически)  │
└─────────────────┘          └──────────────────┘
```

## 🚀 Быстрый старт

### Предварительные требования

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 10GB+ свободного места на диске

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd medical-mvp
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Django
ENV=loc
DEBUG=True
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
POSTGRES_DB=db_django
POSTGRES_USER=myroot
POSTGRES_PASSWORD=secure_password_here

# Redis
REDIS_PASSWORD=redis_secure_password

# RabbitMQ
RABBITMQ_PORT=5672
RABBITMQ_DEFAULT_USER=rabbitmq_user
RABBITMQ_DEFAULT_PASS=rabbitmq_password

#GPT
OPENAI_API_KEY=
```

### 3. Запуск с Docker Compose

```bash
# Сборка и запуск всех сервисов
docker-compose -f loc.docker-compose.yml up --build -d

# Проверка статуса сервисов
docker-compose ps

# Просмотр логов
docker-compose logs -f app-medical
```

### 4. Инициализация базы данных

```bash
# Применение миграций
docker-compose exec app-medical python manage.py migrate

# Создание суперпользователя
docker-compose exec app-medical python manage.py createsuperuser

# Или использовать команду для автоматической настройки
docker-compose exec app-medical python manage.py setup_initial_data --create-admin
```

### 5. Проверка работы системы

```bash
# Статус системы
docker-compose exec app-medical python manage.py system_status
```

### 6. Доступ к приложению

- **Веб-интерфейс**: http://localhost:8000
- **Админ-панель**: http://localhost:8000/admin
- **API**: http://localhost:8000/api/
- **Flower (мониторинг Celery)**: http://localhost:9999
- **RabbitMQ Management**: http://localhost:15672

## 📊 Управление данными

### Команды администрирования

```bash
# Статус системы
python manage.py system_status

# Очистка просроченных файлов
python manage.py cleanup_data --expired-files

# Полная очистка всех данных
python manage.py cleanup_data --all

# Создание тестовых данных
python manage.py generate_test_data --users 5 --analyses-per-user 10

# Резервное копирование
python manage.py backup_data --output-dir ./backups

# Резервное копирование конкретного пользователя
python manage.py backup_data --user-id 1 --include-raw-data
```

### Мониторинг

```bash
# Логи приложения
tail -f logs/medical_mvp.log

# Логи безопасности
tail -f logs/security.log

# Статус Celery workers
celery -A medical_mvp inspect active

# Статистика Celery
celery -A medical_mvp inspect stats

# Flower веб-интерфейс
# Открыть http://localhost:9999
```

## 🔒 Безопасность

### Принципы безопасности

1. **Минимальное время хранения**: Оригинальные файлы удаляются через 60 секунд
2. **Индивидуальное шифрование**: Каждый пользователь имеет уникальный AES-256 ключ
3. **Полный аудит**: Все действия логируются в SecurityLog
4. **Изоляция данных**: Пользователи видят только свои данные
5. **HTTPS обязательно**: В продакшене весь трафик должен быть зашифрован

### Соответствие стандартам

- ✅ **GDPR Article 17**: Автоматическое "право на забвение"
- ✅ **HIPAA Technical Safeguards**: Минимизация времени обработки
- ✅ **ISO 27001**: Стандарты информационной безопасности
- ✅ **152-ФЗ РФ**: Обработка персональных данных с немедленным удалением

### Проверка безопасности

```bash
# Проверка неудаленных файлов
python manage.py system_status

# Принудительная очистка
python manage.py cleanup_data --expired-files

# Анализ логов безопасности
python manage.py shell
>>> from medical_analysis.models import SecurityLog
>>> SecurityLog.objects.filter(action='DATA_ACCESS').count()
```

### Периодические задачи безопасности (Celery Beat)

- **Очистка просроченных файлов**: каждые 5 минут
- **Проверка удаления файлов**: каждый час
- **Очистка старых логов безопасности**: ежедневно (>90 дней)
- **Проверка здоровья системы**: каждые 30 минут

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
python -m pytest

# Конкретный модуль
python -m pytest tests/test_file_processor.py

# С покрытием кода
python -m pytest --cov=medical_analysis

# Тесты безопасности
python -m pytest tests/test_security.py -v

# Подробный вывод
python -m pytest -vv
```

### Тестовые данные

```bash
# Создание тестовых пользователей и анализов
python manage.py generate_test_data --users 5 --analyses-per-user 10

# Тестовые логины:
# testuser1 / testpass123
# testuser2 / testpass123
# testuser3 / testpass123
# ...
```

## 📈 API Документация

### Аутентификация

```http
# Регистрация нового пользователя
POST /api/auth/register/
Content-Type: application/json

{
    "username": "newuser",
    "email": "user@example.com",
    "password": "securepass123",
    "password_confirm": "securepass123"
}

# Вход
POST /api/auth/login/
Content-Type: application/json

{
    "username": "newuser",
    "password": "securepass123"
}

# Выход
POST /api/auth/logout/
Authorization: Token <your-token>
```

### Загрузка файлов

```http
# Загрузить файл для анализа
POST /api/upload/
Authorization: Token <your-token>
Content-Type: multipart/form-data

file: <binary-file>

# Проверить статус обработки
GET /api/upload/status/?session_id=123
Authorization: Token <your-token>
```

### Медицинские данные

```http
# Получить все анализы пользователя
GET /api/medical-data/
Authorization: Token <your-token>

# Получить конкретный анализ
GET /api/medical-data/{id}/
Authorization: Token <your-token>

# Получить временную шкалу анализов
GET /api/medical-data/timeline/
Authorization: Token <your-token>

# Сравнить два анализа
GET /api/medical-data/compare/?id1=1&id2=2
Authorization: Token <your-token>
```

### Профиль пользователя

```http
# Получить профиль
GET /api/profile/me/
Authorization: Token <your-token>

# Обновить язык интерфейса
PATCH /api/profile/update_language/
Authorization: Token <your-token>
Content-Type: application/json

{
    "language_preference": "ru"  # или "en"
}
```

### Пример использования API (Python)

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Регистрация
response = requests.post(f"{BASE_URL}/api/auth/register/", json={
    "username": "newuser",
    "email": "user@example.com",
    "password": "securepass123",
    "password_confirm": "securepass123"
})
print(response.json())

# 2. Вход и получение токена
response = requests.post(f"{BASE_URL}/api/auth/login/", json={
    "username": "newuser",
    "password": "securepass123"
})
token = response.json()["token"]
headers = {"Authorization": f"Token {token}"}

# 3. Загрузка файла
with open("analysis.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(f"{BASE_URL}/api/upload/", 
                           files=files, 
                           headers=headers)
    session_id = response.json()["session_id"]
    print(f"Session ID: {session_id}")

# 4. Проверка статуса обработки
response = requests.get(f"{BASE_URL}/api/upload/status/?session_id={session_id}", 
                       headers=headers)
print(response.json())

# 5. Получение всех анализов
response = requests.get(f"{BASE_URL}/api/medical-data/", headers=headers)
print(response.json())
```

## 🌐 Развертывание в продакшене

### Требования к серверу

- **CPU**: 2+ ядра
- **RAM**: 4+ GB (рекомендуется 8GB)
- **SSD**: 50+ GB
- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **SSL сертификат**: Обязательно для HTTPS

### Подготовка продакшен окружения

```bash
# 1. Обновление системы
sudo apt update && sudo apt upgrade -y

# 2. Установка Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 3. Клонирование на сервер
git clone <repository-url> /opt/medical-mvp
cd /opt/medical-mvp

# 4. Настройка переменных окружения
cp .env.example .env.production
nano .env.production  # Отредактировать с продакшен настройками

# 5. Создание директорий
mkdir -p ssl logs backups

# 6. SSL сертификаты (Let's Encrypt)
# Поместить сертификаты в ssl/cert.pem и ssl/key.pem
# или использовать certbot для автоматического получения

# 7. Запуск продакшен окружения
docker-compose -f docker-compose.production.yml up -d

# 8. Проверка статуса
docker-compose ps
```

### Продакшен конфигурация (.env.production)

```env
ENV=production
DEBUG=False
SECRET_KEY=<very-long-random-secret-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Использовать сильные пароли!
POSTGRES_PASSWORD=<strong-db-password>
REDIS_PASSWORD=<strong-redis-password>
RABBITMQ_DEFAULT_PASS=<strong-rabbitmq-password>

# SSL
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Sentry (опционально, для мониторинга ошибок)
SENTRY_DSN=https://your-sentry-dsn
```

### Настройка Nginx для SSL

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 20M;

    location / {
        proxy_pass http://app-medical:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Мониторинг продакшена

```bash
# Статус всех сервисов
docker-compose ps

# Логи в реальном времени
docker-compose logs -f

# Использование ресурсов
docker stats

# Здоровье системы
docker-compose exec app-medical python manage.py system_status
```

### Резервное копирование

```bash
# Ручное резервное копирование базы данных
docker-compose exec postgres-medical pg_dump -U myroot db_django > backup_$(date +%Y%m%d).sql

# Настройка автоматического резервного копирования (cron)
# Добавить в crontab:
0 2 * * * cd /opt/medical-mvp && docker-compose exec -T postgres-medical pg_dump -U myroot db_django > /opt/medical-mvp/backups/backup_$(date +\%Y\%m\%d).sql
```

## 🐳 Docker Сервисы

### Архитектура контейнеров

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
├──────────────┬──────────────┬──────────────┬────────────┤
│   Nginx      │  App-Medical │   Celery     │  Celery    │
│   :80/:443   │    :8000     │   Workers    │   Beat     │
├──────────────┴──────────────┴──────────────┴────────────┤
│              Infrastructure Layer                        │
├──────────────┬──────────────┬──────────────┬────────────┤
│  PostgreSQL  │    Redis     │  RabbitMQ    │   Flower   │
│    :5432     │    :6379     │ :5672/:15672 │   :9999    │
└──────────────┴──────────────┴──────────────┴────────────┘
```

### Описание сервисов

- **app-medical**: Django приложение (веб-интерфейс + API)
- **postgres-medical**: PostgreSQL 15.4 (основная БД)
- **redis**: Redis 7 (кэш + очереди)
- **rabbitmq**: RabbitMQ 3.13 (message broker для Celery)
- **celery_default**: Celery worker (обработка файлов)
- **celery_beat**: Celery beat (планировщик периодических задач)
- **flower**: Flower (мониторинг Celery)
- **nginx**: Nginx (обратный прокси, статические файлы)

## 🤝 Вклад в проект

### Процесс разработки

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения следуя conventional commits
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

### Стандарты кодирования

- **Python**: PEP 8, type hints обязательны
- **Линтер**: Ruff (настроен в pyproject.toml)
- **Форматирование**: 120 символов на строку
- **Тесты**: Покрытие > 80%
- **Документация**: Docstrings для всех публичных методов
- **Логирование**: Использовать структурированное логирование

### Git Commit Messages

Следуйте формату Conventional Commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Типы:
- `feat`: новая функциональность
- `fix`: исправление ошибки
- `refactor`: рефакторинг
- `test`: добавление тестов
- `docs`: изменение документации
- `chore`: обслуживание кода
- `perf`: улучшение производительности

Пример:

```
feat(api): add medical data comparison endpoint

- implement compare endpoint in MedicalDataViewSet
- add comparison logic for two analysis results
- include validation for same analysis type
- add tests for comparison functionality

Closes #42
```

## 📝 Лицензия

Этот проект лицензирован под MIT License - смотрите файл [LICENSE](LICENSE) для деталей.

## 🆘 Поддержка и контакты

- **Документация**: [docs/](docs/)
- **Issue Tracker**: [GitHub Issues](https://github.com/your-org/medical-mvp/issues)
- **Безопасность**: security@yourdomain.com
- **Поддержка**: support@yourdomain.com

## 📊 Дорожная карта

### v1.1 (в разработке)
- [ ] GPT-4 интеграция для медицинских рекомендаций
- [ ] Экспорт анализов в PDF
- [ ] Email уведомления о готовности анализа
- [ ] Расширенная визуализация данных

### v1.2 (планируется)
- [ ] React Native мобильное приложение
- [ ] Дополнительные типы анализов (моча, иммунология)
- [ ] Интеграция с медицинскими лабораториями
- [ ] Машинное обучение для прогнозов трендов

### v2.0 (будущее)
- [ ] Поддержка DICOM медицинских изображений
- [ ] Телемедицина интеграция
- [ ] Многопользовательские организации
- [ ] Расширенная аналитика и отчеты
- [ ] GraphQL API

## ⚡ Производительность

### Оптимизация

- Использование Redis для кэширования
- Асинхронная обработка файлов через Celery
- Индексы БД для быстрых запросов
- Nginx для статических файлов
- Connection pooling для PostgreSQL

### Рекомендации по масштабированию

- Horizontal scaling: увеличить количество Celery workers
- Vertical scaling: увеличить ресурсы контейнеров
- Database replication для read-heavy нагрузок
- Load balancer перед Nginx для высоких нагрузок

## 🔍 Устранение неполадок

### Частые проблемы

**Файлы не обрабатываются**
```bash
# Проверить Celery workers
docker-compose logs celery_default

# Проверить RabbitMQ
docker-compose exec rabbitmq rabbitmqctl list_queues
```

**Ошибки OCR**
```bash
# Проверить установку Tesseract
docker-compose exec app-medical tesseract --version

# Проверить языковые пакеты
docker-compose exec app-medical tesseract --list-langs
```

**Проблемы с БД**
```bash
# Проверить подключение к PostgreSQL
docker-compose exec app-medical python manage.py dbshell

# Проверить миграции
docker-compose exec app-medical python manage.py showmigrations
```

## 📚 Дополнительные ресурсы

- [Django Documentation](https://docs.djangoproject.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Made with ❤️ for better healthcare**