FROM python:3.11.9

WORKDIR /app

COPY requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt \
    && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.2 \
    torchvision==0.17.2

COPY worker/weights.py worker/
RUN PYTHONPATH=. python -c 'from worker import weights; weights.download_all()' && \
    ln -s /root/.cache/torch/hub/checkpoints/vgg19-dcbb9e9d.pth models/vgg19-dcbb9e9d.pth

COPY worker worker/
COPY conf/worker.py conf/
COPY common ./common

CMD ["rq", "worker", "-c", "conf.worker", "-w", "conf.worker.Worker"]
