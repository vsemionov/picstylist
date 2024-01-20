FROM python:3.11.7

WORKDIR /app

# install packages before copying the whole project to make use of docker's build cache
COPY requirements.txt ./
#RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY conf/gunicorn.py conf/
COPY common ./common
COPY app.py ./
COPY web ./web
COPY templates ./templates

RUN mkdir -p /app/data

EXPOSE 8000
CMD ["gunicorn", "-c", "/app/conf/gunicorn.py", "app:app"]
