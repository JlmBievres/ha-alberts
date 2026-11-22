ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM $BUILD_FROM
RUN apk add --no-cache python3 py3-yaml git openssh-client tzdata
COPY app /app
WORKDIR /app
CMD ["python3", "-u", "/app/app.py"]
