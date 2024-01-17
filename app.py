from flask import Flask, request, g, url_for, abort, redirect, render_template, make_response, send_from_directory
from werkzeug.utils import secure_filename

from web import settings


app = Flask(__name__)
settings.configure(app)


@app.before_request
def before_request():
    g.request_id = request.headers.get('X-Request-ID') or 'none'


@app.route('/', methods=['GET', 'POST'])
def index():
    app.logger.info(request.headers) ###
    import time ###
    time.sleep(2) ###
    if request.method == 'POST':
        content_file = request.files['content']
        style_file = request.files['style']
        content_filename = secure_filename(content_file.filename)
        style_filename = secure_filename(style_file.filename)
        redirect_url = url_for('status', job_id='123')
        return redirect(redirect_url)
    return render_template('index.html')


@app.route('/s/<uuid:job_id>/')
def status(job_id):
    return {}


@app.route('/x/<uuid:job_id>/')
def result(job_id):
    if job_id == '123':
        abort(404)
    return make_response()


@app.route('/x/<uuid:job_id>/<path:filename>')
def image(job_id, filename):
    dirname = f'results/{job_id}'
    response = send_from_directory(dirname, filename)
    return response


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html', error=error), 404
