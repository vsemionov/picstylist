import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

from flask import current_app, request, g
from flask.logging import default_handler
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_httpauth import HTTPBasicAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import click
import redis
from rq import Queue, Worker
from rq_scheduler import Scheduler
import rq_dashboard.cli
from flask_sock import Sock
from cachetools import cached, TTLCache
import sentry_sdk

from common import VERSION, config, database
from web import utils


RATE_LIMIT = '5/minute;50/hour;200/day'
MAX_QUEUE_SIZE_PER_WORKER = 100
MAX_UPLOAD_SIZE_MB = 10
MAX_RESOLUTION_MP = 25
ALLOWED_FORMATS = ['JPEG', 'PNG']
ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']
DEFAULT_STRENGTH = 75
RESULT_FORMAT = ('png', 'image/png')
RESULT_TTL_MINUTES = 30
JOB_KWARGS = {
    'job_timeout': 30,
    'result_ttl': RESULT_TTL_MINUTES * 60,
    'ttl': 30 * 60,
    'failure_ttl': 30 * 60
}
USE_WEBSOCKET = True
LISTEN_ALWAYS_REFRESH = False
STATUS_UPDATE_TIMEOUT = JOB_KWARGS['ttl']
STATUS_UPDATE_INTERVAL = 2
AJAX_TIMEOUT = 30
PORTAINER_PORT = int(os.environ['PORTAINER_PORT'])
PREVENT_JOB_PROBING = False


logger = logging.getLogger(__name__)


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = g.get('request_id', 'n/a') or 'none'
        return True


def get_data_dir(app):
    return Path(app.root_path) / 'data'


def get_jobs_dir(app):
    return get_data_dir(app) / config.JOBS_DIR


@cached(cache=TTLCache(maxsize=1, ttl=60))
def get_max_queue_size(queue):
    return MAX_QUEUE_SIZE_PER_WORKER * max(Worker.count(queue=queue), 1)


def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = database.connect(current_app.config['DATABASE'])
        g.db = db
    return db


def configure(app):
    @app.cli.command('init-db')
    def init_db_command():
        db = get_db()
        with current_app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf-8'))
        click.echo('Initialized the database.')

    @app.teardown_appcontext
    def close_db(e=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    @app.before_request
    def before_request():
        g.request_id = request.headers.get('X-Request-ID')

    @app.context_processor
    def settings():
        return {'settings': sys.modules[__name__]}

    def verify_password(username, password):
        return username == admin_username and password == admin_password

    # Python
    utils.filter_warnings(os.environ['WARNING_FILTERS'])

    # Flask
    app.config['DATABASE'] = str(get_data_dir(app) / config.DATABASE)
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE_MB * 1024 * 1024 * 3 // 2

    # Logging
    app.logger.setLevel(logging.INFO)
    default_handler.addFilter(RequestIDLogFilter())
    default_handler.setFormatter(logging.Formatter(f'[%(request_id)s] {config.LOG_FORMAT}'))

    # ProxyFix
    x_for, x_proto = [int(s.strip()) for s in os.environ['PROXY_X_FOR_PROTO'].split(':')]
    if x_for or x_proto:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto)

    # Admin
    admin_username = os.environ['ADMIN_USERNAME']
    admin_password = os.environ['ADMIN_PASSWORD']
    if not (admin_username and admin_password):
        raise ValueError('ADMIN_USERNAME and ADMIN_PASSWORD must be set.')

    # Flask-HTTPAuth
    auth = HTTPBasicAuth(realm='Restricted Access')
    auth.verify_password(verify_password)

    # Redis
    redis_url = f'redis://{os.environ["REDIS_HOST"]}'
    redis_pool = redis.BlockingConnectionPool.from_url(redis_url, max_connections=1000, timeout=5, socket_timeout=5)
    redis_client = redis.Redis.from_pool(redis_pool)

    # Flask-Limiter
    limiter_logger = logging.getLogger('flask-limiter')
    limiter_logger.addHandler(default_handler)
    limiter_logger.setLevel(logging.INFO)
    limiter = Limiter(get_remote_address, app=app, application_limits=['100/minute'], storage_uri=f'redis://',
        storage_options={'connection_pool': redis_pool}, strategy='fixed-window', swallow_errors=False)
    auth_limit = limiter.shared_limit('3 per 15 minutes', scope='auth',
        deduct_when=lambda response: response.status_code == 401)

    # RQ
    job_queue = Queue(name=config.DEFAULT_QUEUE, connection=redis_client)
    system_queue = Queue(name=config.SYSTEM_QUEUE, connection=redis_client)
    scheduler = Scheduler(queue=system_queue, connection=system_queue.connection)
    for job in scheduler.get_jobs():
        scheduler.cancel(job)
        job.delete()
    start_time = datetime.utcnow()
    scheduler.schedule(start_time, 'worker.tasks.log_stats', description='log_stats', id='log_stats', interval=60,
        timeout=30)
    scheduler.schedule(start_time, 'worker.tasks.cleanup_data', description='cleanup_data', args=[JOB_KWARGS],
        id='cleanup_data', interval=(15 * 60), timeout=30)
    scheduler.schedule(start_time + timedelta(minutes=1.1), 'worker.tasks.health_check', description='health_check',
        id=config.HEALTH_CHECK_JOB_ID, interval=config.HEALTH_CHECK_INTERVAL, timeout=30, at_front=True)
    scheduler.cron('0 3 * * *', 'worker.tasks.maintenance', description='maintenance', id='maintenance', timeout=30)

    # RQ Dashboard
    app.config['RQ_DASHBOARD_REDIS_URL'] = redis_url
    app.config.from_object(rq_dashboard.default_settings)
    rq_dashboard.web.setup_rq_connection(app)
    rq_dashboard.cli.add_basic_auth(rq_dashboard.blueprint, admin_username, admin_password, realm=auth.realm)
    auth_limit(rq_dashboard.blueprint)
    app.register_blueprint(rq_dashboard.blueprint, url_prefix='/admin/rq')

    # Flask-Sock
    app.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': 25, 'max_message_size': 128}
    sock = Sock(app)

    return app, auth, limiter, sock, auth_limit, job_queue


app_env = os.environ['APP_ENV']
sentry_dsn = os.environ['SENTRY_DSN']
service_name = os.environ['SERVICE_NAME']
if sentry_dsn:
    sentry_sdk.init(sentry_dsn, release=VERSION, environment=app_env, server_name=service_name)
else:
    if app_env != 'development':
        raise ValueError('SENTRY_DSN is required on remote environments.')
    logger.warning('SENTRY_DSN not set, Sentry disabled.')
