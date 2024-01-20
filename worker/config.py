import logging.config

from common.integration import configure_sentry


# TODO: test
logging_config = {
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


def configure():
    logging.config.dictConfig(logging_config)

    # TODO: test
    configure_sentry()
