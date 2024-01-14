import os

bind = "0.0.0.0:8000"
workers = os.cpu_count()
worker_class = "gthread"
threads = 10

accesslog = "-"
access_log_format = '%(h)s - %(u)s [%(t)s] "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" "%({x-forwarded-for}i)s" %({x-request-id}i)s'
