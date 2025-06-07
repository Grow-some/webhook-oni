FROM python:3.13-slim

WORKDIR /app
RUN apt-get update && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
COPY healthcheck.py .
RUN pip install --no-cache-dir -r requirements.txt
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && echo $TZ > /etc/timezone
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 healthcheck.py
CMD ["python3", "webhook_server.py"]