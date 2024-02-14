FROM python:3.11.8

WORKDIR /app

COPY requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt

COPY worker/models.py worker/
RUN python worker/models.py && ln -s /Users/victor/.cache/torch/hub/checkpoints/vgg19-dcbb9e9d.pth \
    models/vgg19-dcbb9e9d.pth

COPY conf/worker.py conf/
COPY common ./common
COPY worker ./worker

CMD ["rq", "worker", "-c", "conf.worker", "-w", "conf.worker.Worker"]
