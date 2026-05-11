from celery import Celery

from app.config import get_settings


settings = get_settings()

celery_app = Celery(
    "email_content_extractor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_default_queue="default",
    task_routes={
        "app.workers.tasks.process_email": {"queue": "default"},
        "app.workers.tasks.publish_to_wordpress": {"queue": "publish"},
        "app.workers.tasks.send_whatsapp_notification": {"queue": "notify"},
        "app.workers.tasks.check_imap_inbox": {"queue": "default"},
        "app.workers.tasks.cleanup_old_logs": {"queue": "default"},
    },
    beat_schedule={
        "check-imap-inbox-every-60-seconds": {
            "task": "app.workers.tasks.check_imap_inbox",
            "schedule": 60.0,
        },
        "cleanup-old-logs-daily": {
            "task": "app.workers.tasks.cleanup_old_logs",
            "schedule": 86400.0,
        },
    },
    timezone="UTC",
    enable_utc=True,
)

app = celery_app
