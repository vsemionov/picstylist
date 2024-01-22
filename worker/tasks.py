import os
import errno
import logging
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


def style_image(base_path, content_filename, style_filename, result_filename):
    try:
        import worker.model
        return worker.model.fast_style_transfer(base_path, content_filename, style_filename, result_filename)
    finally:
        for path in [os.path.join(base_path, filename) for filename in [content_filename, style_filename]]:
            try:
                os.remove(path)
            except OSError:
                pass


def cleanup_data(data_dir, job_kwargs):
    ttl = sum(job_kwargs[k] for k in ['job_timeout', 'result_ttl', 'ttl'])
    max_time = (datetime.now() - timedelta(seconds=ttl)).timestamp()
    n_files = 0
    n_dirs = 0
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
