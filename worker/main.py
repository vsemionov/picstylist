#!/usr/bin/env python

import sys
import os
from pathlib import Path

from redis import Redis
from rq import SimpleWorker


if __name__ == '__main__':
    sys.path.append(str(Path(__file__).parent / '..'))

    from common import globals
    from worker import config

    config.configure()

    # preload libraries
    import model

    w = SimpleWorker([globals.SYSTEM_QUEUE, globals.DEFAULT_QUEUE], connection=Redis(os.environ['REDIS_HOST']))
    w.log_result_lifespan = False
    w.work()
