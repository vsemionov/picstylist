FROM python:3.11.7

WORKDIR /app

# install packages before copying the whole project to make use of docker's build cache
COPY requirements-worker.txt ./
#RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install --no-cache-dir -r requirements-worker.txt

COPY worker/model.py worker/
RUN python worker/model.py

COPY common ./common
COPY worker ./worker

RUN mkdir -p /app/data

CMD ["python", "worker/main.py"]
