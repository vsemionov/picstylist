#!/usr/bin/env python

import sys
import os
from pathlib import Path

from redis import Redis
from rq import SimpleWorker


def main():
    sys.path.append(str(Path(__file__).parent.parent))

    from common import globals
    from worker import config

    config.configure()

    # preload libraries
    import tasks
    import model

    queues = [globals.SYSTEM_QUEUE, globals.DEFAULT_QUEUE]
    redis_client = Redis(os.environ['REDIS_HOST'], socket_connect_timeout=15)  # socket_timeout is handled by rq
    worker_class = SimpleWorker
    worker = worker_class(queues, connection=redis_client)
    worker.log_result_lifespan = False
    worker.work()


if __name__ == '__main__':
    main()
