from arq.connections import RedisSettings

from app.core.config import settings
from app.worker.tasks import process_document_task

class WorkerSettings:
    functions = [
        process_document_task,
    ]

    redis_settings = RedisSettings(
        host = settings.redis_host,
        port = settings.redis_port,
    )