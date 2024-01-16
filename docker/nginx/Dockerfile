FROM nginx:1.25.3

WORKDIR /app

COPY . .

COPY /etc/picstylist/ssl /etc/nginx/ssl

RUN cp conf/nginx.conf /etc/nginx/nginx.conf
