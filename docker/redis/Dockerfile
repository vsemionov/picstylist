FROM redis:7.2.4

WORKDIR /app

COPY conf/redis.conf /etc/redis/redis.conf

CMD ["redis-server", "/etc/redis/redis.conf"]
