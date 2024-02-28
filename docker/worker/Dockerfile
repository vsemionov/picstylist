FROM python:3.11.8

WORKDIR /app

COPY requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt && pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu filelock==3.9.0 fsspec==2023.4.0 jinja2==3.1.2 mpmath==1.3.0 \
    networkx==3.2.1 sympy==1.12 torch==2.2.1 torchvision==0.17.1

COPY worker worker/
RUN PYTHONPATH=. python worker/models.py && ln -s /root/.cache/torch/hub/checkpoints/vgg19-dcbb9e9d.pth \
    models/vgg19-dcbb9e9d.pth

COPY conf/worker.py conf/
COPY common ./common

CMD ["rq", "worker", "-c", "conf.worker", "-w", "conf.worker.Worker"]
