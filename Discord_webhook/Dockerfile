FROM python:3.13-slim

WORKDIR /app
RUN apt-get update && \
    rm -rf /var/lib/apt/lists/*
COPY ./ /app
RUN pip install --no-cache-dir -r requirements.txt
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && echo $TZ > /etc/timezone
ENTRYPOINT ["python3", "webhook_server.py"]