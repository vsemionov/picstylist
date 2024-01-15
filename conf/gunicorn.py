import os

bind = '0.0.0.0:8000'
workers = os.cpu_count()
worker_class = 'gevent'
worker_connections = 1024
