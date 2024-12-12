import os
import sys

from rq import SimpleWorker
import sentry_sdk

from common import VERSION, config


REDIS_URL = f'redis://{os.environ["REDIS_HOST"]}?socket_connect_timeout=15'  # socket_timeout is handled by rq
QUEUES = [config.SYSTEM_QUEUE, config.DEFAULT_QUEUE]
SENTRY_DSN = os.environ['SENTRY_DSN']
DICT_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': config.LOG_FORMAT
        }
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stderr'
        }
    },
    'loggers': {
        'root': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        }
    }
}


class Worker(SimpleWorker):
    def __init__(self, *args, **kwargs):
        # preload libraries
        import worker.tasks
        import worker.models

        super().__init__(*args, **kwargs)
        self.log_result_lifespan = False


fqn = f'{Worker.__module__}.{Worker.__qualname__}'
assert os.getenv('RQ_WORKER_CLASS') == fqn or fqn in sys.argv

app_env = os.environ['APP_ENV']
service_name = os.environ['SERVICE_NAME']
sentry_sdk.init(SENTRY_DSN, release=VERSION, environment=app_env, server_name=service_name)
