from celery import Celery

from app.core.config import settings


def make_celery_app() -> Celery:
    app = Celery(
        "chatbot_workers",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )

    # Basic defaults. You can tune concurrency from env/worker CLI.
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )

    return app


celery_app = make_celery_app()

