FROM python:3.11.8

WORKDIR /app

COPY requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt && pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.2 \
    torchvision==0.17.2

COPY worker worker/
RUN PYTHONPATH=. python worker/models.py && ln -s /root/.cache/torch/hub/checkpoints/vgg19-dcbb9e9d.pth \
    models/vgg19-dcbb9e9d.pth

COPY conf/worker.py conf/
COPY common ./common

CMD ["rq", "worker", "-c", "conf.worker", "-w", "conf.worker.Worker"]
