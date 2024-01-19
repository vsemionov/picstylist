import uuid

from flask import Flask, request, g, url_for, abort, redirect, render_template, make_response, send_from_directory, \
    session, jsonify
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
        # TODO: validate form and secure CSRF
        file = request.files['file']
        session_id = session.get('id')
        if session_id is None:
            session_id = uuid.uuid4()
            session['id'] = session_id
        redirect_url = url_for('result', session_id=session_id, job_id=123)
        return redirect(redirect_url)
    return render_template('index.html')


@app.route('/api/status/<uuid:session_id>/<uuid:job_id>/')
def status(session_id, job_id):
    if session_id != session.get('id'):
        return jsonify({}), 403
    return jsonify({})


@app.route('/x/<uuid:session_id>/<uuid:job_id>/')
def result(session_id, job_id):
    if session_id != session.get('id'):
        abort(403)
    return make_response()


@app.route('/x/<uuid:session_id>/<uuid:job_id>/<path:filename>')
def image(session_id, job_id, filename):
    if session_id != session.get('id'):
        abort(403)
    dirname = f'results/{job_id}'
    response = send_from_directory(dirname, filename)
    return response


@app.route('/model/')
def model():
    return render_template('model.html')


@app.route('/math/')
def math():
    return render_template('math.html')


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


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
