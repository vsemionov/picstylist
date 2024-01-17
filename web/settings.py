import logging

from flask import g
from flask.logging import default_handler


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = g.request_id
        return True


def configure(app):
    app.logger.setLevel(logging.INFO)
    default_handler.addFilter(RequestIDLogFilter())
    default_handler.setFormatter(logging.Formatter(
        '[%(process)d:%(threadName)s] [%(request_id)s] [%(name)s] %(levelname)s: %(message)s'))

    # TODO: ProxyFix middleware
    # TODO: review settings reference
    # TODO: review potohub settings
    # TODO: check if this is per file or total
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
