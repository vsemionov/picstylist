import os

bind = '0.0.0.0:8000'
workers = os.cpu_count()
worker_class = 'gthread'
threads = 10
