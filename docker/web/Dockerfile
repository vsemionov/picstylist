FROM python:3.11.9

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY schema.sql ./
COPY conf/gunicorn.py conf/
COPY common ./common
COPY app.py ./
COPY web ./web
COPY templates ./templates

EXPOSE 8000
CMD ["gunicorn", "-c", "/app/conf/gunicorn.py", "app:app"]
