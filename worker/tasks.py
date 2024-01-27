import os
import re
import io
import time
import uuid
import errno
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta

import requests
import docker
import numpy as np
from PIL import Image
from redis import Redis
from rq import Queue

from common import globals, NAME
from common.stats import start_job, end_job, StatsError


logger = logging.getLogger(__name__)


JOBS_DIR = Path(__file__).parent.parent / 'data' / globals.JOBS_DIR


def style_image(subdir, content_filename, style_filename, strength, result_filename, stats=True):
    stat_id = None
    try:
        stat_id = start_job()
    except StatsError as e:
        logger.error('Failed to start stats job: %s', e)

    from . import model

    base_path = JOBS_DIR / subdir
    succeeded = False

    try:
        start_time = time.time()
        result = model.fast_style_transfer(base_path, content_filename, style_filename, strength, result_filename)
        succeeded = True
        logger.info('Finished in %.1f seconds.', time.time() - start_time)
        return result

    finally:
        if stats and stat_id is not None:
            try:
                end_job(stat_id, succeeded)
            except StatsError as e:
                logger.error('Failed to end stats job: %s', e)
        for path in [base_path / filename for filename in [content_filename, style_filename]]:
            try:
                path.unlink(missing_ok=True)
            except OSError as e:
                logger.error('Failed to remove %s: %s', path, e)
                continue


def log_stats():
    default_queue_len = len(Queue(name=globals.DEFAULT_QUEUE, connection=redis_client))
    system_queue_len = len(Queue(name=globals.SYSTEM_QUEUE, connection=redis_client))
    logger.info('Queues: %d default, %d system.', default_queue_len, system_queue_len)


def cleanup_data(job_kwargs):
    ttl = sum(job_kwargs[k] for k in ['job_timeout', 'result_ttl', 'ttl'])
    max_time = (datetime.now() - timedelta(seconds=ttl)).timestamp()
    n_files, n_dirs = 0, 0
    jobs_dir = os.path.normpath(JOBS_DIR)
    for dirpath, dirnames, filenames in os.walk(jobs_dir, topdown=False):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            try:
                if os.path.getmtime(path) < max_time:
                    os.remove(path)
                    n_files += 1
            except FileNotFoundError:
                continue
        if dirpath == jobs_dir:
            continue
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
                n_dirs += 1
        except FileNotFoundError:
            continue
        except OSError as e:
            if e.errno == errno.ENOTEMPTY:
                continue
            raise
    logger.info('Removed %d files and %d directories.', n_files, n_dirs)


def health_check():
    required_containers = {'web', 'worker', 'scheduler', 'redis', 'nginx'}
    running_containers = set()
    docker_client = docker.from_env()
    containers = docker_client.containers.list()
    for container in containers:
        match = re.match(rf'^{NAME}([-_])(.*)\1\d+$', container.name)
        if not match:
            continue
        service = match.group(2)
        if service not in required_containers:
            continue
        if container.health != 'healthy':
            if container.health != 'starting':
                logger.error('Container %s is unhealthy.', container.name)
            continue
        running_containers.add(service)
    not_running_containers = required_containers - running_containers
    if not_running_containers:
        raise RuntimeError('Not all containers are running.')

    response = requests.get(f'http://{os.environ["NGINX_HOST"]}/')
    if response.status_code != 200:
        raise RuntimeError('Web server is down.')

    job_id = str(uuid.uuid4())
    subdir = f'{job_id}/{job_id}'
    test_filename = 'test.png'
    job_dir = JOBS_DIR / subdir
    job_dir.mkdir(parents=True, exist_ok=True)
    with open(job_dir / test_filename, 'wb') as f:
        test_image.seek(0)
        shutil.copyfileobj(test_image, f)
    queue = Queue(name=globals.DEFAULT_QUEUE, connection=redis_client)
    args = subdir, test_filename, test_filename, 100, 'result.png'
    kwargs = {'stats': False}
    job_id = globals.IMAGE_CHECK_JOB_ID  # if re-enqueuing with the same id causes problems, use the uuid and return it
    queue.enqueue(style_image, args=args, kwargs=kwargs, job_id=job_id, at_front=True, job_timeout=30,
        result_ttl=globals.HEALTH_CHECK_VALIDITY, ttl=globals.HEALTH_CHECK_VALIDITY,
        failure_ttl=globals.HEALTH_CHECK_VALIDITY)
    logger.info('Enqueued job: %s', job_id)


redis_client = Redis(host=os.environ['REDIS_HOST'])
test_image = io.BytesIO()
Image.fromarray(np.zeros((128, 128, 3), dtype=np.uint8)).save(test_image, format='PNG')
