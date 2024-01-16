FROM python:3.11.7

WORKDIR /app

# install packages before copying the whole project to make use of docker's build cache
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-c", "/app/conf/gunicorn.py", "app:app"]

EXPOSE 8000
