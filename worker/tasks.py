import os
import time
import errno
import logging
from pathlib import Path
from datetime import datetime, timedelta


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
    for dirpath, dirnames, filenames in os.walk(DATA_DIR, topdown=False):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            try:
                if os.path.getmtime(path) < max_time:
                    os.remove(path)
                    n_files += 1
            except FileNotFoundError:
                continue
        if dirpath == DATA_DIR:
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
