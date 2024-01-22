import uuid
from pathlib import Path

from flask import Flask, url_for, abort, redirect, render_template, send_from_directory, session, jsonify
from werkzeug.utils import secure_filename
from jinja2 import TemplateNotFound

from web import settings
from web import forms


app = Flask(__name__)
app, limiter, image_queue = settings.configure(app)


def prepare_job(session_id, job_id, content_image, style_image):
    root = settings.get_data_dir(app) / str(session_id) / str(job_id)
    content_filename = Path(secure_filename(content_image.filename))
    content_path = root / content_filename
    style_path = root / secure_filename(style_image.filename)
    result_stem = root / f'{content_filename.stem} (styled)'
    root.mkdir(parents=True, exist_ok=True)
    content_image.save(content_path)
    style_image.save(style_path)
    return content_path, style_path, result_stem


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

        content_path, style_path, result_stem = prepare_job(session_id, job_id, content_image, style_image)
        image_queue.enqueue('worker.tasks.style_image', content_path, style_path, result_stem, job_id=str(job_id),
            **settings.JOB_KWARGS)
        app.logger.info('Enqueued job %s (%s).', 'style_image', job_id)

        redirect_url = url_for('result', session_id=session_id, job_id=job_id)
        return redirect(redirect_url)

    limits = {
        'max_upload_size_mb': settings.MAX_UPLOAD_SIZE_MB,
        'max_resolution_mp': settings.MAX_RESOLUTION_MP
    }
    return render_template('index.html', form=form, limits=limits)


@app.route('/api/status/<uuid:session_id>/<uuid:job_id>/')
def status(session_id, job_id):
    if session_id != session.get('id'):
        return jsonify({}), 403
    return jsonify({})


@app.route('/cancel/<uuid:session_id>/<uuid:job_id>/')
def cancel(session_id, job_id):
    if session_id != session.get('id'):
        abort(403)
    return ''


@app.route('/s/<uuid:session_id>/<uuid:job_id>/')
def waiting(session_id, job_id):
    if session_id != session.get('id'):
        abort(403)
    return ''


@app.route('/x/<uuid:session_id>/<uuid:job_id>/')
def result(session_id, job_id):
    if session_id != session.get('id'):
        abort(403)
    return ''


@app.route('/x/<uuid:session_id>/<uuid:job_id>/<path:filename>')
def image(session_id, job_id, filename):
    if session_id != session.get('id'):
        abort(403)
    dirname = f'results/{session_id}/{job_id}'
    response = send_from_directory(dirname, filename)
    return response


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
    return render_template('errors/413.html', max_size=settings.MAX_UPLOAD_SIZE_MB), 403


@app.errorhandler(429)
def too_many_requests(e):
    lockout_time = ' '.join(e.description.split(' ')[-2:])
    return render_template('errors/429.html', limit=e.description, lockout_time=lockout_time), 429


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500


if __name__ == '__main__':
    app.run()
