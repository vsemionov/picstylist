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

from common import NAME, config, database, history


DATA_DIR = Path(__file__).parent.parent / 'data'
JOBS_DIR = DATA_DIR / config.JOBS_DIR


logger = logging.getLogger(__name__)


def style_transfer(func, subdir, content_filename, style_filename, strength, result_filename, with_history=True):
    succeeded = False
    base_path = JOBS_DIR / subdir

    db = None
    hist_id = None
    if with_history:
        db = database.connect(DATA_DIR / config.DATABASE)

    try:
        if with_history:
            hist_id = history.start_job(db, meta=func.__name__)

        start_time = time.time()
        result = func(base_path, content_filename, style_filename, strength, result_filename)
        logger.info('Finished in %.1f seconds.', time.time() - start_time)
        succeeded = True
        return result

    finally:
        if db is not None:
            try:
                if hist_id is not None:
                    history.end_job(db, hist_id, succeeded)
            finally:
                db.close()
        for path in [base_path / filename for filename in [content_filename, style_filename]]:
            try:
                path.unlink(missing_ok=True)
            except OSError as e:
                logger.error('Failed to remove %s: %s', path, e)
                continue


def fast_style_transfer(*args, **kwargs):
    from . import models
    return style_transfer(models.fast_style_transfer, *args, **kwargs)


def iterative_style_transfer(*args, **kwargs):
    from . import models
    return style_transfer(models.iterative_style_transfer, *args, **kwargs)


def log_stats():
    default_queue_len = len(Queue(name=config.DEFAULT_QUEUE, connection=redis_client))
    system_queue_len = len(Queue(name=config.SYSTEM_QUEUE, connection=redis_client))
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
                logger.warning('Container %s is unhealthy.', container.name)
            continue
        running_containers.add(service)
    not_running_containers = required_containers - running_containers
    if not_running_containers:
        raise RuntimeError('Not all containers are running.')

    response = requests.get(f'http://{os.environ["NGINX_HOST"]}/')
    if response.status_code != 200:
        raise RuntimeError('Web server is down.')

    filename = 'test.png'
    job_id = f'test-{uuid.uuid4().hex}'
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    with open(job_dir / filename, 'wb') as f:
        test_image.seek(0)
        shutil.copyfileobj(test_image, f)
    queue = Queue(name=config.DEFAULT_QUEUE, connection=redis_client)
    args = job_id, filename, filename, 100, 'result.png'
    kwargs = {'with_history': False}
    job_id = config.IMAGE_CHECK_JOB_ID  # if re-enqueuing with the same id causes problems, use the uuid and return it
    queue.enqueue(fast_style_transfer, description='test_style_transfer', args=args, kwargs=kwargs, job_id=job_id,
        at_front=True, job_timeout=30, result_ttl=config.HEALTH_CHECK_VALIDITY, ttl=config.HEALTH_CHECK_VALIDITY,
        failure_ttl=config.HEALTH_CHECK_VALIDITY)
    logger.info('Enqueued job: %s', job_id)


def maintenance():
    db = database.connect(DATA_DIR / config.DATABASE)
    try:
        n_deleted = history.cleanup(db)
        logger.info('Deleted %d old job history entries.', n_deleted)
    finally:
        db.close()


redis_client = Redis(os.environ['REDIS_HOST'])
test_image = io.BytesIO()
Image.fromarray(np.zeros((128, 128, 3), dtype=np.uint8)).save(test_image, format='PNG')
