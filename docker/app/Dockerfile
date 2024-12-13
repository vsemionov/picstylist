FROM python:3.11.11 AS base

WORKDIR /app

COPY lockfile.txt ./
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r lockfile.txt \
    && rm lockfile.txt


FROM base AS web

COPY schema.sql ./
COPY conf/gunicorn.py conf/
COPY common ./common
COPY app.py ./
COPY web ./web
COPY templates ./templates

EXPOSE 8000
CMD ["gunicorn", "-c", "/app/conf/gunicorn.py", "app:app"]


FROM base AS worker

COPY worker/weights.py worker/
RUN PYTHONPATH=. python -c 'from worker import weights; weights.download_all()' \
    && rm -rf worker

COPY worker worker/
COPY conf/worker.py conf/
COPY common ./common

CMD ["rq", "worker", "-c", "conf.worker", "-w", "conf.worker.Worker"]


FROM base AS scheduler

CMD ["rqscheduler"]
