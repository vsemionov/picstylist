FROM redis:7.4.1

WORKDIR /app

COPY conf/redis.conf /etc/redis/

CMD ["redis-server", "/etc/redis/redis.conf"]
