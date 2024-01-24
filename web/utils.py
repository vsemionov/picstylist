import time
from functools import wraps

from flask import make_response
from rq import Worker
from rq.job import Job
from rq.results import Result
from rq.exceptions import NoSuchJobError

from common import globals
from . import settings


def no_cache(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    return wrapped_view


def check_health(app, job_queue):
    start_time = time.time()
    if len(job_queue) >= settings.get_max_queue_size(job_queue) // 2:
        app.logger.error('Health check failed: queue size is too large.')
        return False
    if len([w for w in Worker.all(job_queue.connection) if w.get_state() in ['idle', 'busy']]) < 1:
        app.logger.error('Health check failed: no workers are available.')
        return False
    for job_id in [globals.HEALTH_CHECK_JOB_ID, globals.IMAGE_CHECK_JOB_ID]:
        try:
            job = Job.fetch(job_id, job_queue.connection)
        except NoSuchJobError:
            app.logger.error('Health check failed: job %s does not exist.', job_id)
            return False
        result = job.latest_result()
        if result is None:
            # don't assume health is ok if the 1st job is still running to avoid zeroing any downtime alert grace timer
            app.logger.error('Health check failed: job %s has no result.', job_id)
            return False
        if result.type != Result.Type.SUCCESSFUL:
            app.logger.error('Health check failed: job %s failed.', job_id)
            return False
        if result.created_at.timestamp() < start_time - globals.HEALTH_CHECK_VALIDITY:
            app.logger.error('Health check failed: job %s is too old.', job_id)
            return False
    return True
