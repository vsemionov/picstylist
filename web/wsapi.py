import time
import json

from werkzeug.exceptions import Forbidden, NotFound

from web import settings


def listen(ws, job_id):
    # check ssl
    # log connections
    # test http errors
    # close reason not working
    # check timeout (and how does the ping work?)

    from app import app, job_queue, get_job_or_abort

    def update_status(refresh):
        terminal_status = {'finished', 'failed', 'canceled', 'stopped'}
        status = job.get_status(refresh=refresh)
        position = job_queue.get_job_position(job) if status == 'queued' else None
        app.logger.info('Job status: %s', status)
        cur_state = (status, position)
        if cur_state != state[0]:
            ws.send(json.dumps({'status': status, 'position': position}))
            state[0] = cur_state
        return status is not None and status not in terminal_status

    end_time = time.time() + settings.STATUS_UPDATE_TIMEOUT

    try:
        job = get_job_or_abort(job_id)
    except Forbidden:
        error = 'Forbidden'
        app.logger.info(error)
        ws.close(reason=error)
        return
    except NotFound:
        error = 'Not Found'
        app.logger.info(error)
        ws.close(reason=error)
        return

    state = [(None, None)]
    app.logger.info(f'Listening for job status updates: {job_id}')
    if update_status(False):
        pubsub = job_queue.connection.pubsub()  # no ignore_subscribe_messages=True to trigger an initial status fetch
        try:
            db = job_queue.connection.connection_pool.connection_kwargs.get('db', 0)
            pubsub.subscribe(f'__keyspace@{db}__:{job.key.decode()}')
            while True:
                timeout = min(end_time - time.time(), settings.STATUS_UPDATE_INTERVAL)  # poll for queue position
                if timeout <= 0:
                    error = 'Job failed to finalize in time.'
                    app.logger.info(error)
                    ws.close(reason=error)
                    break
                message = pubsub.get_message(timeout=timeout)
                if not update_status(message is not None or settings.LISTEN_ALWAYS_REFRESH):
                    break
                ws.receive(timeout=0)  # undocumented, but needed to trigger the ping/pong timeout

        finally:
            pubsub.close()


def configure(sock):
    sock.route('/listen/<job_id>/')(listen)
