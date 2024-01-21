import os
import logging

from flask import request, g
from flask.logging import default_handler
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from rq import Queue

from conf import gunicorn as gunicorn_conf
from common.integration import configure_sentry


RATE_LIMIT = '5/minute;50/hour;200/day'
JOB_KWARGS = dict(job_timeout=30, result_ttl=(2 * 60 * 60), ttl=(30 * 60), failure_ttl=(2 * 60 * 60))
MAX_UPLOAD_SIZE_MB = 10
ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']
ALLOWED_FORMATS = ['JPEG', 'PNG']
MAX_RESOLUTION_MP = 25


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = g.get('request_id', 'n/a') or 'none'
        return True


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
    queue = Queue(connection=redis_client)

    return app, limiter, queue


configure_sentry(with_flask=True)
