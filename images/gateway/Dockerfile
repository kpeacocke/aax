ARG NGINX_VERSION=1.30-alpine
FROM nginx:${NGINX_VERSION}

RUN apk upgrade --no-cache

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
