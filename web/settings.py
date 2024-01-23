import os
import sys
import logging
from pathlib import Path
from datetime import datetime

from flask import request, g
from flask.logging import default_handler
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
from rq import Queue, Worker
from rq_scheduler import Scheduler
import rq_dashboard.cli
from cachetools import cached, TTLCache

from conf import gunicorn as gunicorn_conf
from common.integration import configure_sentry


RATE_LIMIT = '5/minute;50/hour;200/day'
MAX_QUEUE_SIZE_PER_WORKER = 200
MAX_UPLOAD_SIZE_MB = 10
MAX_RESOLUTION_MP = 25
ALLOWED_FORMATS = ['JPEG', 'PNG']
ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']
RESULT_FORMAT = ('png', 'image/png')
RESULT_TTL_MINUTES = 30
JOB_KWARGS = {
    'job_timeout': 30,
    'result_ttl': RESULT_TTL_MINUTES * 60,
    'ttl': 30 * 60,
    'failure_ttl': 30 * 60,
    'description': 'style_image'
}
AJAX_POLL_INTERVAL = 2
AJAX_TIMEOUT = 30


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = g.get('request_id', 'n/a') or 'none'
        return True


def get_data_dir(app):
    return Path(app.root_path) / 'data'


@cached(cache=TTLCache(maxsize=1, ttl=60))
def get_max_queue_size(queue):
    return MAX_QUEUE_SIZE_PER_WORKER * max(Worker.count(queue.connection), 1)


def configure(app):
    @app.before_request
    def before_request():
        g.request_id = request.headers.get('X-Request-ID')

    @app.context_processor
    def settings():
        return {'settings': sys.modules[__name__]}

    # Flask
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE_MB * 1024 * 1024 * 3 // 2

    # Logging
    app.logger.setLevel(logging.INFO)
    default_handler.addFilter(RequestIDLogFilter())
    default_handler.setFormatter(logging.Formatter('[%(request_id)s] %(levelname)s in %(name)s: %(message)s'))

    # ProxyFix
    x_for, x_proto = [int(s.strip()) for s in os.environ['PROXY_X_FOR_PROTO'].split(':')]
    if x_for or x_proto:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto)

    # Redis
    redis_url = f"redis://{os.environ['REDIS_HOST']}"
    redis_pool = redis.BlockingConnectionPool.from_url(redis_url, max_connections=(gunicorn_conf.threads + 1),
        timeout=5, socket_timeout=5)
    redis_client = redis.Redis.from_pool(redis_pool)

    # Flask-Limiter
    limiter_logger = logging.getLogger('flask-limiter')
    limiter_logger.addHandler(default_handler)
    limiter_logger.setLevel(logging.INFO)
    limiter = Limiter(get_remote_address, app=app, application_limits=['100/minute'], storage_uri=f'redis://',
        storage_options={'connection_pool': redis_pool}, strategy='fixed-window', swallow_errors=False)

    # RQ
    # TODO: error in cleanup task
    job_queue = Queue(connection=redis_client)
    system_queue = Queue(name='system', connection=redis_client)
    scheduler = Scheduler(queue=system_queue, connection=system_queue.connection)
    for job in scheduler.get_jobs():
        job.delete()
    # TODO: schedule only once
    scheduler.schedule(datetime.utcnow(), 'worker.tasks.cleanup_data', args=[JOB_KWARGS], description='cleanup_data',
        interval=(15 * 60), timeout=30)

    # RQ Dashboard
    username = os.environ['RQ_DASHBOARD_USERNAME']
    password = os.environ['RQ_DASHBOARD_PASSWORD']
    assert len(username) > 0 and len(password) > 0
    app.config['RQ_DASHBOARD_REDIS_URL'] = redis_url
    app.config.from_object(rq_dashboard.default_settings)
    rq_dashboard.web.setup_rq_connection(app)
    rq_dashboard.cli.add_basic_auth(rq_dashboard.blueprint, username, password)
    limiter.limit('3 per 15 minutes', deduct_when=lambda response: response.status_code in [401, 403]) \
        (rq_dashboard.blueprint)
    app.register_blueprint(rq_dashboard.blueprint, url_prefix='/rq')

    return app, limiter, job_queue


configure_sentry(with_flask=True)
