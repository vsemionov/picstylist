import uuid
from pathlib import Path

from flask import Flask, request, session, abort, url_for, redirect, render_template, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.exceptions import Forbidden, NotFound
from jinja2 import TemplateNotFound

from common import history
from web import settings
from web import forms
from web import utils


app = Flask(__name__)
app, auth, limiter, auth_limit, job_queue = settings.configure(app)


def check_session_id(session_id):
    if session_id != session.get('id'):
        abort(403)


def get_job_or_404(session_id, job_id):
    job = job_queue.fetch_job(str(job_id))
    if job is None or job.meta['session_id'] != str(session_id):
        abort(404)
    return job


@app.route('/', methods=['GET', 'POST'])
@limiter.limit(settings.RATE_LIMIT, methods=['POST'])
def index():
    form = forms.UploadForm()
    if form.validate_on_submit():
        if job_queue.count >= settings.get_max_queue_size(job_queue):
            return render_template('errors/busy.html')

        content_image = form.content_image.data
        style_image = form.style_image.data
        strength = form.strength.data

        session_id = session.get('id')
        if session_id is None:
            session_id = uuid.uuid4()
            session['id'] = session_id
        job_id = uuid.uuid4()

        subdir = Path(str(session_id)) / str(job_id)
        job_dir = settings.get_jobs_dir(app) / subdir
        content_filename = Path(secure_filename(content_image.filename))
        style_filename = secure_filename(style_image.filename)
        result_filename = f'{content_filename.stem} (styled).{settings.RESULT_FORMAT[0]}'
        job_dir.mkdir(parents=True, exist_ok=True)
        content_image.save(job_dir / content_filename)
        style_image.save(job_dir / style_filename)

        args = str(subdir), str(content_filename), style_filename, strength, result_filename
        meta = {'session_id': str(session_id)}
        job_queue.enqueue('worker.tasks.style_image', args=args, job_id=str(job_id), meta=meta, **settings.JOB_KWARGS)
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
    fields = {'status': status}
    if status == 'queued':
        fields['position'] = job_queue.get_job_position(job)
    app.logger.info('Job status: %s', status)
    return jsonify(fields), 200


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
    check_session_id(session_id)
    job = get_job_or_404(session_id, job_id)
    status = job.get_status(refresh=False)
    position = job_queue.get_job_position(job) if status == 'queued' else None
    filename = job.args[-1]
    cancel_form = forms.CancelForm()
    return render_template('result.html', status=status, position=position, filename=filename, cancel_form=cancel_form)


@app.route('/x/<uuid:session_id>/<uuid:job_id>/<path:filename>')
def image(session_id, job_id, filename):
    check_session_id(session_id)
    job = get_job_or_404(session_id, job_id)
    if job.get_status(refresh=False) != 'finished':
        abort(404)
    if filename != job.args[-1]:
        abort(404)
    path = settings.get_jobs_dir(app) / job.args[0] / filename
    kwargs = {'as_attachment': True, 'download_name': filename} if 'download' in request.args else {}
    return send_file(path, mimetype=settings.RESULT_FORMAT[1], **kwargs)


@app.route('/status/')
def server_status():
    return '', 200 if utils.check_health(app, job_queue) else 503


@app.route('/<path:name>.html')
def page(name):
    try:
        return render_template(f'pages/{name}.html')
    except TemplateNotFound:
        abort(404)


@app.route('/admin/stats/')
@auth_limit
@auth.login_required
def stats():
    job_stats = history.get_job_stats(settings.get_db())
    return render_template('admin/stats.html', job_stats=job_stats)


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
@app.errorhandler(500)
def error(e):
    code = e.code
    return render_template(f'errors/{code}.html'), code


@app.errorhandler(429)
def too_many_requests(e):
    lockout_time = ' '.join(e.description.split(' ')[-2:])
    return render_template('errors/429.html', limit=e.description, lockout_time=lockout_time), 429


if __name__ == '__main__':
    app.run()
