import os
import logging

from flask import g
from flask.logging import default_handler
from werkzeug.middleware.proxy_fix import ProxyFix
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from . import VERSION


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = g.request_id
        return True


def configure(app):
    app.logger.setLevel(logging.INFO)
    default_handler.addFilter(RequestIDLogFilter())
    default_handler.setFormatter(logging.Formatter('[%(request_id)s] %(levelname)s in %(name)s: %(message)s'))

    # TODO: review settings reference
    # TODO: review potohub settings
    # TODO: check if this is per file or total
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    x_for, x_proto = [int(s.strip()) for s in os.environ['PROXY_X_FOR_PROTO'].split(':')]
    if x_for or x_proto:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto)

    return app


sentry_sdk.init(os.environ['SENTRY_DSN'], release=VERSION, environment=os.environ['APP_ENV'],
    integrations=[FlaskIntegration()])
