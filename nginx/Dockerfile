#FROM nginx:stable-alpine
FROM nginx:1.27-alpine

# 放在 .env dockerfile 不吃
ENV GRAFANA_SSL=/C=TW/ST=Taipei/L=New_Taipei/O=Robert_Cloud/OU=Technology/CN=robertcloud.net/
## Generate certificate
RUN apk add --update openssl && \
    rm -rf /var/cache/apk/*

COPY ssl.conf /etc/nginx/ssl.conf

#RUN openssl req -x509 -out /etc/nginx/ssl.crt -keyout /etc/nginx/ssl.key -newkey rsa:4096 -nodes -sha256 -subj ${GRAFANA_SSL} 
RUN openssl req -x509 -new -nodes -sha256 -utf8 -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl.key -out /etc/nginx/ssl.crt -config /etc/nginx/ssl.conf
## Copy configuration
#COPY default.conf /etc/nginx/templates/default.conf.template
COPY nginx.conf /etc/nginx/nginx.conf
COPY proxy.conf /etc/nginx/conf.d/proxy.conf
COPY http_headers.conf /etc/nginx/conf.d/http_headers.conf
#RUN mkdir -p /data/json
#COPY ./json /data/json

CMD ["nginx", "-g", "daemon off;"]
#CMD ["envsubst < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]