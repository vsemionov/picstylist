FROM python:3.11.8

WORKDIR /app

COPY requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt && pip install --no-cache-dir torch==2.2.0+cpu \
    torchvision==0.17.0 --index-url https://download.pytorch.org/whl/cpu

COPY worker worker/
RUN PYTHONPATH=. python worker/models.py && ln -s /Users/victor/.cache/torch/hub/checkpoints/vgg19-dcbb9e9d.pth \
    models/vgg19-dcbb9e9d.pth

COPY conf/worker.py conf/
COPY common ./common

CMD ["rq", "worker", "-c", "conf.worker", "-w", "conf.worker.Worker"]
