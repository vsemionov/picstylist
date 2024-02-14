FROM python:3.11.8

WORKDIR /app

COPY requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt

COPY worker/models.py worker/
RUN python worker/models.py && ln -s ~/.keras/models/vgg19_weights_tf_dim_ordering_tf_kernels_notop.h5 \
    models/vgg19_weights_tf_dim_ordering_tf_kernels_notop.h5

COPY conf/worker.py conf/
COPY common ./common
COPY worker ./worker

CMD ["rq", "worker", "-c", "conf.worker", "-w", "conf.worker.Worker"]
