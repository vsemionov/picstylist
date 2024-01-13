FROM python:3.11.7

WORKDIR /app

# install packages before copying the whole project to make use of docker cache
COPY requirements.txt ./
RUN pip install -U pip setuptools wheel
RUN pip install -r requirements.txt

COPY . ./

CMD ["gunicorn", "-c", "/app/conf/gunicorn.py", "app:app"]
