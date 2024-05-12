FROM python:3.11.9

WORKDIR /app

COPY requirements-scheduler.txt ./
RUN pip install --no-cache-dir -r requirements-scheduler.txt

CMD ["rqscheduler"]
