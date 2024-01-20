#!/usr/bin/env python

import os

from redis import Redis
from rq import Worker

# preload libraries
from . import model


def style_image(content_path, style_path, output_name):
    try:
        return model.fast_style_transfer(content_path, style_path, output_name)
    finally:
        try:
            os.remove(content_path)
            os.remove(style_path)
        except OSError:
            pass


worker = Worker(['default'], connection=Redis(os.environ['REDIS_HOST']))
worker.work()
