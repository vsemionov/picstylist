FROM python:3.11.7

WORKDIR /app

# install packages before copying the whole project to make use of docker's build cache
COPY requirements-worker.txt ./
#RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install --no-cache-dir -r requirements-worker.txt

COPY conf/worker.py conf/
COPY worker ./worker

RUN mkdir model
RUN python worker/model.py

CMD ["python", "worker/main.py"]
