from flask import Flask, request, render_template


app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        pass
    return render_template('index.html')


@app.route('/s/<uuid:job_id>/')
def status(job_id):
    pass


@app.route('/x/<uuid:job_id>/')
def result(job_id):
    pass


@app.route('/x/<uuid:job_id>/<path:filename>')
def image(job_id, filename):
    pass
