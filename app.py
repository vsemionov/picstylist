from flask import Flask, request, g, url_for, abort, redirect, render_template, make_response, send_from_directory
from werkzeug.utils import secure_filename
from flask_limiter import RateLimitExceeded

from web import settings


app = Flask(__name__)
app, limiter = settings.configure(app)


@app.before_request
def before_request():
    g.request_id = request.headers.get('X-Request-ID')


@app.route('/', methods=['GET', 'POST'])
@limiter.limit('5/minute;50/hour;200/day', methods=['POST'])
def index():
    if request.method == 'POST':
        try:
            with limiter.limit('3 / hour'):
                use_captcha = False
        except RateLimitExceeded:
            use_captcha = True
        content_file = request.files['content']
        style_file = request.files['style']
        content_filename = secure_filename(content_file.filename)
        style_filename = secure_filename(style_file.filename)
        redirect_url = url_for('status', session_id=123, job_id=123)
        return redirect(redirect_url)
    return render_template('index.html')


# TODO: add vary header
@app.route('/s/<uuid:session_id>/<uuid:job_id>/')
def status(session_id, job_id):
    return {}


# TODO: add vary header
@app.route('/x/<uuid:session_id>/<uuid:job_id>/')
def result(session_id, job_id):
    if job_id == 123:
        abort(404)
    return make_response()


# TODO: add vary header
@app.route('/x/<uuid:session_id>/<uuid:job_id>/<path:filename>')
def image(session_id, job_id, filename):
    dirname = f'results/{job_id}'
    response = send_from_directory(dirname, filename)
    return response


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(429)
def too_many_requests(e):
    lockout_time = ' '.join(e.description.split(' ')[-2:])
    return render_template('429.html', limit=e.description, lockout_time=lockout_time), 429


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
