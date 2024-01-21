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
    import numpy
    import tensorflow
    import tensorflow_hub
    from PIL import Image
    # NOTE: Ideally, we would preload the model too, but it turns out TensorFlow is not fork-safe and deadlocks.
    # The standard solution seems to be to deploy TensorFlow Serving, but that's a bit overkill for this project.

    redis_client = Redis(os.environ['REDIS_HOST'])
    queues = ['system', 'images']
    w = Worker(queues, connection=redis_client)
    w.log_result_lifespan = False
    w.work()
