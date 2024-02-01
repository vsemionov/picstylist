import logging

from . import tasks


logger = logging.getLogger(__name__)


def style_transfer(job, connection, *args, **kwargs):
    subdir, content_filename, style_filename = job.args[:3]
    base_path = tasks.JOBS_DIR / subdir
    for path in [base_path / filename for filename in [content_filename, style_filename]]:
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            logger.error('Failed to remove %s: %s', path, e)
            continue
