import os
import logging
import sentry_sdk
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.rq import RqIntegration

from common import VERSION


def configure_sentry(with_flask=False):
    app_env = os.environ['APP_ENV']
    sentry_dsn = os.environ['SENTRY_DSN']
    if not sentry_dsn:
        if app_env != 'development':
            raise ValueError('SENTRY_DSN is required on remote environments.')
        logging.getLogger(__name__).warning('SENTRY_DSN not set, Sentry disabled.')
        return

    service_name = os.environ['SERVICE_NAME']
    integrations = [RedisIntegration(), RqIntegration()]
    if with_flask:
        from sentry_sdk.integrations.flask import FlaskIntegration
        integrations = [FlaskIntegration()] + integrations
    sentry_sdk.init(sentry_dsn, release=VERSION, environment=app_env, server_name=service_name,
        integrations=integrations)
