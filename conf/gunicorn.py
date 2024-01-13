import os

bind = "127.0.0.1:8000"
workers = os.cpu_count()
worker_class = "gthread"
threads = 10
