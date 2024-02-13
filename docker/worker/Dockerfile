FROM python:3.11.8

WORKDIR /app

COPY requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt

COPY worker/model.py worker/
RUN python worker/model.py

COPY conf/worker.py conf/
COPY common ./common
COPY worker ./worker

CMD ["rq", "worker", "-c", "conf.worker", "-w", "conf.worker.Worker"]
