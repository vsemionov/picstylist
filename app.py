import uuid
from pathlib import Path

from flask import Flask, session, abort, url_for, redirect, render_template, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.exceptions import Forbidden, NotFound
from jinja2 import TemplateNotFound

from web import settings
from web import forms


app = Flask(__name__)
app, limiter, image_queue = settings.configure(app)


def check_session_id(session_id):
    if session_id != session.get('id'):
        abort(403)


def get_job_or_404(session_id, job_id):
    job = image_queue.fetch_job(str(job_id))
    if job is None or job.meta['session_id'] != str(session_id):
        abort(404)
    return job


@app.route('/', methods=['GET', 'POST'])
@limiter.limit(settings.RATE_LIMIT, methods=['POST'])
def index():
    form = forms.UploadForm()
    if form.validate_on_submit():
        if image_queue.count >= settings.get_max_queue_size(image_queue):
            return render_template('errors/busy.html')

        content_image = form.content_image.data
        style_image = form.style_image.data

        session_id = session.get('id')
        if session_id is None:
            session_id = uuid.uuid4()
            session['id'] = session_id
        job_id = uuid.uuid4()

        data_dir = settings.get_data_dir(app)
        subdir = Path(str(session_id)) / str(job_id)
        job_dir = data_dir / subdir
        content_filename = Path(secure_filename(content_image.filename))
        style_filename = secure_filename(style_image.filename)
        result_filename = f'{content_filename.stem} (styled).{settings.RESULT_FORMAT[0]}'
        job_dir.mkdir(parents=True, exist_ok=True)
        content_image.save(job_dir / content_filename)
        style_image.save(job_dir / style_filename)

        args = str(subdir), str(content_filename), style_filename, result_filename
        meta = {'session_id': str(session_id)}
        image_queue.enqueue('worker.tasks.style_image', args=args, job_id=str(job_id), meta=meta, **settings.JOB_KWARGS)
        app.logger.info('Enqueued job: %s', job_id)

        redirect_url = url_for('result', session_id=session_id, job_id=job_id)
        return redirect(redirect_url)

    return render_template('index.html', form=form)


@app.route('/api/status/<uuid:session_id>/<uuid:job_id>/')
def status(session_id, job_id):
    try:
        check_session_id(session_id)
        job = get_job_or_404(session_id, job_id)
    except Forbidden:
        return jsonify({'error': 'Forbidden'}), 403
    except NotFound:
        return jsonify({'error': 'Not Found'}), 404
    status = job.get_status(refresh=False)
    app.logger.info('Job status: %s', status)
    return jsonify({'status': status}), 200


@app.route('/cancel/<uuid:session_id>/<uuid:job_id>/', methods=['POST'])
def cancel(session_id, job_id):
    check_session_id(session_id)
    form = forms.CancelForm()
    if form.validate_on_submit():
        job = get_job_or_404(session_id, job_id)
        job.cancel()
        app.logger.info('Canceled job: %s', job_id)
    return redirect(url_for('index'))


@app.route('/x/<uuid:session_id>/<uuid:job_id>/')
def result(session_id, job_id):
    # TODO: save link
    check_session_id(session_id)
    job = get_job_or_404(session_id, job_id)
    status = job.get_status(refresh=False)
    filename = job.args[-1]
    cancel_form = forms.CancelForm()
    return render_template('result.html', status=status, filename=filename, cancel_form=cancel_form)


@app.route('/x/<uuid:session_id>/<uuid:job_id>/<path:filename>')
def image(session_id, job_id, filename):
    check_session_id(session_id)
    job = get_job_or_404(session_id, job_id)
    if job.get_status(refresh=False) != 'finished':
        abort(404)
    if filename != job.args[-1]:
        abort(404)
    path = settings.get_data_dir(app) / job.args[0] / filename
    return send_file(path, mimetype=settings.RESULT_FORMAT[1])


@app.route('/<path:name>.html')
def html(name):
    try:
        return render_template(f'pages/{name}.html')
    except TemplateNotFound:
        abort(404)


@app.errorhandler(400)
def bad_request(e):
    return render_template('errors/400.html'), 403


@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(413)
def too_large(e):
    return render_template('errors/413.html'), 403


@app.errorhandler(429)
def too_many_requests(e):
    lockout_time = ' '.join(e.description.split(' ')[-2:])
    return render_template('errors/429.html', limit=e.description, lockout_time=lockout_time), 429


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500


if __name__ == '__main__':
    app.run()
