FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python3", "webhook_server.py"]