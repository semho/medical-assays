import os
from datetime import timedelta
from typing import TypedDict, NotRequired, Any

from celery import Celery
from celery.schedules import crontab

# Устанавливаем переменную окружения для Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_mvp.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


class TaskOptions(TypedDict):
    expires: NotRequired[int]
    queue: NotRequired[str]


class BeetScheduleNode(TypedDict):
    task: str
    schedule: int | float | timedelta | crontab
    args: NotRequired[tuple]
    kwargs: NotRequired[dict[str, Any]]
    options: NotRequired[TaskOptions]


def create_test_celery():
    inner_app = Celery("medical_mvp")
    inner_app.conf.task_always_eager = True
    return inner_app


def config_loggers(*args, **kwags):
    from logging.config import dictConfig
    from django.conf import settings

    dictConfig(settings.LOGGING)


def create_default_celery():
    inner_app = Celery("medical_mvp")
    inner_app.config_from_object("django.conf:settings", namespace="CELERY")

    inner_app.autodiscover_tasks()

    beat_schedule: dict[str, BeetScheduleNode] = {}

    local_beat_schedule: dict[str, BeetScheduleNode] = {}

    # local_beat_schedule.update(
    #     {
    #         "sync_clicklog": {
    #             "task": "django_clickhouse.tasks.sync_clickhouse_model",
    #             "schedule": timedelta(seconds=15),
    #             "args": ["main.clickhouse_models.ClickLogCH"],
    #             "options": {"queue": "celery"},
    #         },
    #         "clean_old_mirror_logs": {
    #             "task": "clean_old_mirror_logs_task",
    #             "schedule": crontab(hour=3, minute=0),
    #         },
    #     },
    # )

    # if SENTRY_ENV in ["development", "production"]:
    #     beat_schedule.update(
    #         {
    #             "sync_clicklog": {
    #                 "task": "django_clickhouse.tasks.sync_clickhouse_model",
    #                 "schedule": timedelta(seconds=15),
    #                 "args": ["main.clickhouse_models.ClickLogCH"],
    #                 "options": {"queue": "celery"},
    #             },
    #             "clean_old_mirror_logs": {
    #                 "task": "clean_old_mirror_logs_task",
    #                 "schedule": crontab(hour=3, minute=0),
    #             },
    #             "cleanup_old_clicklog_records": {
    #                 "task": "cleanup_old_clicklog_records_task",
    #                 "schedule": crontab(hour=2, minute=0),
    #                 "options": {"queue": "default"},
    #             },
    #         },
    #     )

    beat_schedule.update(
        {
            "cleanup_expired_sessions": {
                "task": "medical_analysis.tasks.cleanup_expired_files",
                "schedule": timedelta(minutes=5),
                "options": {"queue": "default"},
            },
        }
    )
    inner_app.conf.beat_schedule = {**local_beat_schedule, **beat_schedule}
    return inner_app


app = create_default_celery()
