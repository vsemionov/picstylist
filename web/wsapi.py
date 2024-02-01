import time
import json

from flask import request
from simple_websocket import Server, ConnectionClosed

from web import settings


def listen(job_id):
    from app import app, job_queue, get_job_or_abort

    def update_status(refresh):
        terminal_status = {'finished', 'failed', 'canceled', 'stopped'}
        status = job.get_status(refresh=refresh)
        position = job_queue.get_job_position(job) if status == 'queued' else None
        cur_state = (status, position)
        if cur_state != state[0]:
            app.logger.info('Job status: %s', status)
            ws.send(json.dumps({'status': status, 'position': position}))
            state[0] = cur_state
        return status is not None and status not in terminal_status

    end_time = time.time() + settings.STATUS_UPDATE_TIMEOUT
    job = get_job_or_abort(job_id)
    state = [(None, None)]
    app.logger.info('Listen: %s', job_id)
    ws = Server(request.environ, ping_interval=settings.WEBSOCKET_PING_INTERVAL, max_message_size=128)
    try:
        if update_status(False):
            pubsub = job_queue.connection.pubsub()  # no ignore_subscribe_messages to trigger an initial status fetch
            try:
                db = job_queue.connection.connection_pool.connection_kwargs.get('db', 0)
                pubsub.subscribe(f'__keyspace@{db}__:{job.key.decode()}')
                while True:
                    timeout = min(end_time - time.time(), settings.STATUS_UPDATE_INTERVAL)  # poll for queue position
                    if timeout <= 0:
                        error = 'Job failed to finalize in time.'
                        app.logger.info(error)
                        ws.close(message=error)
                        break
                    message = pubsub.get_message(timeout=timeout)
                    if not update_status(message is not None or settings.LISTEN_ALWAYS_REFRESH):
                        break
                    data = ws.receive(timeout=0)
                    if data is not None:
                        break
            finally:
                pubsub.close()
    except ConnectionClosed:
        pass
    finally:
        if ws.connected:
            ws.close()
    app.logger.info('Listen finished.')
    return ''


def configure(app):
    app.route('/ws/listen/<job_id>/', websocket=True)(listen)
