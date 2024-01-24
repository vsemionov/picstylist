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
from rq import get_current_job, Queue

from common import globals, NAME


logger = logging.getLogger(__name__)


DATA_DIR = Path(__file__).parent.parent / 'data'


def style_image(subdir, content_filename, style_filename, strength, result_filename):
    from . import model
    base_path = DATA_DIR / subdir
    try:
        start_time = time.time()
        result = model.fast_style_transfer(base_path, content_filename, style_filename, strength, result_filename)
        logger.info('Finished in %.1f seconds.', time.time() - start_time)
        return result
    finally:
        for path in [base_path / filename for filename in [content_filename, style_filename]]:
            try:
                path.unlink()
            except OSError:
                continue


def cleanup_data(job_kwargs):
    ttl = sum(job_kwargs[k] for k in ['job_timeout', 'result_ttl', 'ttl'])
    max_time = (datetime.now() - timedelta(seconds=ttl)).timestamp()
    n_files, n_dirs = 0, 0
    data_dir = os.path.normpath(DATA_DIR)
    for dirpath, dirnames, filenames in os.walk(data_dir, topdown=False):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            try:
                if os.path.getmtime(path) < max_time:
                    os.remove(path)
                    n_files += 1
            except FileNotFoundError:
                continue
        if dirpath == data_dir:
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
        logger.error('Not all containers are running: %s', not_running_containers)
        return False

    response = requests.get('http://localhost/')
    if response.status_code != 200:
        logger.error('Web server is down.')
        return False

    job_id = str(uuid.uuid4())
    job_dir = f'{job_id}/{job_id}'
    test_filename = 'test.png'
    (DATA_DIR / job_dir).mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / job_dir / test_filename, 'wb') as f:
        shutil.copyfileobj(test_image, f)
    queue = Queue(name=globals.DEFAULT_QUEUE, connection=get_current_job().connection)
    args = job_dir, test_filename, test_filename, 100, 'result.png'
    queue.enqueue(style_image, args=args, job_id=job_id, at_front=True, job_timeout=30,
        result_ttl=globals.HEALTH_CHECK_VALIDITY, ttl=globals.HEALTH_CHECK_VALIDITY,
        failure_ttl=globals.HEALTH_CHECK_VALIDITY)


test_image = io.BytesIO()
Image.fromarray(np.zeros((128, 128, 3), dtype=np.uint8)).save(test_image, format='PNG')
