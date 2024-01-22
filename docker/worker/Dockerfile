FROM python:3.11.7

WORKDIR /app

COPY requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt

COPY worker/model.py worker/

COPY common ./common
COPY worker ./worker

CMD ["python", "worker/main.py"]
