# Medical MVP - Медицинский Анализатор

Безопасная платформа для автоматизированного анализа медицинских результатов с максимальной защитой персональных данных.

## 🚀 Ключевые особенности

- **Безопасность "Process & Delete"**: Файлы удаляются через 60 секунд
- **End-to-end шифрование**: Индивидуальные ключи для каждого пользователя
- **OCR распознавание**: Автоматическое извлечение данных из PDF и изображений
- **Анализ динамики**: Отслеживание изменений показателей во времени
- **Мультиязычность**: Поддержка русского и английского языков
- **Веб + API**: Полнофункциональный веб-интерфейс и REST API

## 📋 Поддерживаемые анализы

- Общий анализ крови (ОАК)
- Биохимический анализ крови
- Гормональные анализы

## 🛠 Технологический стек

- **Backend**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL + Redis
- **Async Processing**: Celery
- **OCR**: Tesseract + PyMuPDF
- **Security**: AES-256 шифрование
- **Frontend**: Django Templates + HTMX + Bootstrap
- **Deployment**: Docker + Docker Compose

## 🏗 Архитектура безопасности

```
Загрузка файла → Временное хранение → OCR → Парсинг → Шифрование → Удаление оригинала
     ↓              (60 секунд)         ↓       ↓         ↓           ↓
Пользователь    Temp файл на сервере    AI  Структура  AES-256   Только зашифр.
                                            данных     ключ       данные в БД
```

## 🚀 Быстрый старт

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
# Основные настройки
DEBUG=False
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# База данных
DB_NAME=medical_mvp
DB_USER=postgres
DB_PASSWORD=secure_password_here
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Безопасность
ENCRYPTION_KEY_LENGTH=32
FILE_RETENTION_SECONDS=60
MAX_PROCESSING_TIME=300
```

### 3. Запуск с Docker

```bash
# Сборка и запуск всех сервисов
docker-compose up --build -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f web
```

### 4. Инициализация системы

```bash
# Создание суперпользователя и настройка
docker-compose exec web python manage.py setup_initial_data --create-admin

# Проверка статуса системы
docker-compose exec web python manage.py system_status
```

### 5. Доступ к приложению

- **Веб-интерфейс**: http://localhost:8000
- **Админ-панель**: http://localhost:8000/admin
- **API документация**: http://localhost:8000/api/docs/
- **Логин по умолчанию**: admin / admin123

## 🔧 Локальная разработка

### Установка зависимостей

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Установка Tesseract OCR
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng

# macOS:
brew install tesseract tesseract-lang

# Windows: скачать с https://github.com/UB-Mannheim/tesseract/wiki
```

### Настройка базы данных

```bash
# Запуск PostgreSQL и Redis через Docker
docker-compose up -d db redis

# Применение миграций
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser
```

### Запуск разработческого сервера

```bash
# Терминал 1: Django
python manage.py runserver

# Терминал 2: Celery Worker
celery -A medical_mvp worker -l info

# Терминал 3: Celery Beat (периодические задачи)
celery -A medical_mvp beat -l info
```

## 📊 Управление данными

### Команды администрирования

```bash
# Статус системы
python manage.py system_status

# Очистка данных
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
tail -f medical_mvp.log

# Логи безопасности
tail -f security.log

# Статус Celery
celery -A medical_mvp inspect active

# Мониторинг через веб
# Установите flower: pip install flower
celery -A medical_mvp flower
# Доступ: http://localhost:5555
```

## 🔒 Безопасность

### Принципы безопасности

1. **Минимальное время хранения**: Файлы удаляются через 60 секунд
2. **Индивидуальное шифрование**: У каждого пользователя свой ключ AES-256
3. **Аудит всех действий**: Полное логирование в SecurityLog
4. **Изоляция данных**: Пользователи видят только свои данные
5. **HTTPS обязательно**: В продакшене весь трафик зашифрован

### Соответствие стандартам

- ✅ **GDPR Article 17**: Автоматическое "право на забвение"
- ✅ **HIPAA Technical Safeguards**: Минимизация времени обработки
- ✅ **ISO 27001**: Стандарты информационной безопасности
- ✅ **152-ФЗ РФ**: Обработка с немедленным удалением

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
```

### Тестовые данные

```bash
# Создание тестовых пользователей и анализов
python manage.py generate_test_data

# Тестовые логины:
# testuser1 / testpass123
# testuser2 / testpass123
# ...
```

## 📈 API

### Основные endpoints

```http
# Аутентификация
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/logout/

# Загрузка файлов
POST /api/upload/
GET  /api/upload/status/?session_id=123

# Данные анализов
GET  /api/medical-data/
GET  /api/medical-data/{id}/
GET  /api/medical-data/timeline/
GET  /api/medical-data/compare/?id1=1&id2=2

# Профиль пользователя
GET  /api/profile/me/
PATCH /api/profile/update_language/
```

### Пример использования API

```python
import requests

# Регистрация
response = requests.post('http://localhost:8000/api/auth/register/', {
    'username': 'newuser',
    'email': 'user@example.com',
    'password': 'securepass123',
    'password_confirm': 'securepass123'
})

# Загрузка файла
files = {'file': open('analysis.pdf', 'rb')}
response = requests.post(
    'http://localhost:8000/api/upload/',
    files=files,
    headers={'Authorization': 'Token your-token-here'}
)

# Получение результатов
response = requests.get(
    'http://localhost:8000/api/medical-data/',
    headers={'Authorization': 'Token your-token-here'}
)
```

## 🌐 Развертывание в продакшене

### Требования к серверу

- **CPU**: 2+ ядра
- **RAM**: 4+ GB
- **SSD**: 50+ GB
- **OS**: Ubuntu 20.04+ / CentOS 8+
- **Docker**: 20.10+
- **SSL сертификат**: Обязательно

### Подготовка продакшен окружения

```bash
# 1. Клонирование на сервер
git clone <repository-url> /opt/medical-mvp
cd /opt/medical-mvp

# 2. Настройка переменных окружения
cp .env.example .env.production
# Отредактировать .env.production с продакшен настройками

# 3. SSL сертификаты
mkdir ssl
# Поместить сертификаты в ssl/cert.pem и ssl/key.pem

# 4. Запуск
docker-compose -f docker-compose.production.yml up -d

# 5. Настройка nginx (если не используете встроенный)
# Скопировать nginx.conf в /etc/nginx/sites-available/
```

### Мониторинг продакшена

```bash
# Статус всех сервисов
docker-compose ps

# Логи в реальном времени
docker-compose logs -f

# Использование ресурсов
docker stats

# Резервное копирование (настроить cron)
0 2 * * * /opt/medical-mvp/backup.sh
```

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

### Стандарты кодирования

- PEP 8 для Python кода
- Покрытие тестами > 80%
- Документация для всех публичных методов
- Логирование всех критических операций

## 📝 Лицензия

Этот проект лицензирован под MIT License - смотрите файл [LICENSE](LICENSE) для деталей.

## 🆘 Поддержка

- **Документация**: [docs/](docs/)
- **Issue tracker**: GitHub Issues
- **Безопасность**: security@example.com
- **Email**: support@example.com

## 📊 Дорожная карта

### v1.1 (следующая версия)
- [ ] GPT интеграция для рекомендаций
- [ ] React Native мобильное приложение
- [ ] Экспорт в PDF отчеты
- [ ] Уведомления по email

### v1.2
- [ ] Дополнительные типы анализов
- [ ] Интеграция с лабораториями
- [ ] Машинное обучение для прогнозов
- [ ] API для внешних систем

### v2.0
- [ ] Поддержка DICOM изображений
- [ ] Телемедицина интеграция
- [ ] Многопользовательские организации
- [ ] Расширенная аналитика