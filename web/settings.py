import os
import logging
from pathlib import Path
from datetime import datetime

from flask import request, g
from flask.logging import default_handler
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from rq import Queue
from rq_scheduler import Scheduler

from conf import gunicorn as gunicorn_conf
from common.integration import configure_sentry


RATE_LIMIT = '5/minute;50/hour;200/day'
MAX_UPLOAD_SIZE_MB = 10
MAX_RESOLUTION_MP = 25
ALLOWED_FORMATS = ['JPEG', 'PNG']
ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']
JOB_KWARGS = {
    'job_timeout': 30,
    'result_ttl': 30 * 60,
    'ttl': 30 * 60,
    'failure_ttl': 30 * 60,
    'description': 'style_image'
}


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = g.get('request_id', 'n/a') or 'none'
        return True


def get_data_dir(app, as_path=True):
    path = Path(app.root_path) / 'data'
    if not as_path:
        path = str(path)
    return path


def configure(app):
    @app.before_request
    def before_request():
        g.request_id = request.headers.get('X-Request-ID')

    app.logger.setLevel(logging.INFO)
    default_handler.addFilter(RequestIDLogFilter())
    default_handler.setFormatter(logging.Formatter('[%(request_id)s] %(levelname)s in %(name)s: %(message)s'))

    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE_MB * 1024 * 1024 * 3 // 2

    x_for, x_proto = [int(s.strip()) for s in os.environ['PROXY_X_FOR_PROTO'].split(':')]
    if x_for or x_proto:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto)

    redis_pool = redis.BlockingConnectionPool.from_url(f"redis://{os.environ['REDIS_HOST']}",
        max_connections=(gunicorn_conf.threads + 1), timeout=5, socket_timeout=5)

    limiter_logger = logging.getLogger('flask-limiter')
    limiter_logger.addHandler(default_handler)
    limiter_logger.setLevel(logging.INFO)

    limiter = Limiter(get_remote_address, app=app, application_limits=['100/minute'], storage_uri=f'redis://',
        storage_options={'connection_pool': redis_pool}, strategy='fixed-window', swallow_errors=False)

    redis_client = redis.Redis.from_pool(redis_pool)
    image_queue = Queue(name='images', connection=redis_client)
    system_queue = Queue(name='system', connection=redis_client)
    scheduler = Scheduler(queue=system_queue, connection=system_queue.connection)
    for job in scheduler.get_jobs():
        job.delete()
    scheduler.schedule(datetime.utcnow(), 'worker.tasks.cleanup_data', description='cleanup_data', interval=(15 * 60),
        timeout=30, args=[get_data_dir(app, as_path=False), JOB_KWARGS])

    return app, limiter, image_queue


configure_sentry(with_flask=True)
