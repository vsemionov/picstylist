import os

bind = '0.0.0.0:8000'
workers = os.cpu_count()
worker_class = 'gthread'
threads = 10

access_log_format = '[%({X-Request-ID}i)s] %(h)s - "%(r)s" %(L)s %(s)s %(b)s "%(f)s" "%(a)s"'
