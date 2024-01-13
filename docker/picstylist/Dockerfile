FROM python:3.11.7

WORKDIR /app

COPY requirements.txt app.py conf ./

RUN pip install -U pip setuptools wheel
RUN pip install -r requirements.txt

CMD ["gunicorn", "-c", "/app/conf/gunicorn.py", "app:app"]
EXPOSE 8000
