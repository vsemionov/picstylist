FROM redis:7.2.4

WORKDIR /app

COPY conf/redis.conf /etc/redis/

CMD ["redis-server", "/etc/redis/redis.conf"]
