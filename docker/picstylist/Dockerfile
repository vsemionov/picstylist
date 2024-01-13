FROM python:3.11.7

WORKDIR /app

COPY requirements.txt app.py ./

RUN pip install pip==23.3.2 setuptools==69.0.3 wheel==0.42.0
RUN pip install -r requirements.txt

# CMD ["python", "app.py"]
