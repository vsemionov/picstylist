#!/usr/bin/env python

import sys
import os
from pathlib import Path

from redis import Redis
from rq import Worker


if __name__ == '__main__':
    sys.path.append(str(Path(__file__).parent / '..'))

    from worker import config
    config.configure()

    # preload libraries
    import worker.model

    w = Worker(['default'], connection=Redis(os.environ['REDIS_HOST']))
    w.work()
