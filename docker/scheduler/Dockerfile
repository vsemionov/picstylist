FROM python:3.12.3

WORKDIR /app

COPY requirements-scheduler.txt ./
RUN pip install --no-cache-dir -r requirements-scheduler.txt

CMD ["rqscheduler"]
