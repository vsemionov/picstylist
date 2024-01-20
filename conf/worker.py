import os


SENTRY_DSN = os.environ['SENTRY_DSN']

DICT_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(levelname)s in %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        'root': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        },
    }
}
