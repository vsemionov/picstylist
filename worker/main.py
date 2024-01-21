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

    w = Worker(['system', 'images'], connection=Redis(os.environ['REDIS_HOST']))
    w.log_result_lifespan = False
    w.work()
