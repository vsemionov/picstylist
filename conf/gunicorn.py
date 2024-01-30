import os
import sys


bind = '0.0.0.0:8000'
workers = os.cpu_count()
worker_class = 'gevent'
worker_connections = 1024
keepalive = 120
timeout = 30

accesslog = '-'
access_log_format = '[%({X-Request-ID}i)s] %(h)s - "%(r)s" %(L)s %(s)s %(b)s "%(f)s" "%(a)s"'


def post_worker_init(worker):
    import sqlite3
    import gsqlite3
    gsqlite3.too_slow = -1  # disable sync execution
    sys.modules[sqlite3.__name__] = gsqlite3
    worker.log.info('Gevent initialized.')
