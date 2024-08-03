FROM redis:7.2.5

WORKDIR /app

COPY conf/redis.conf /etc/redis/

CMD ["redis-server", "/etc/redis/redis.conf"]
