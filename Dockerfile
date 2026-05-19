FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /agent

RUN adduser --disabled-password --gecos "" agentuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config
COPY README.md ./README.md
COPY workspace ./workspace

RUN chown -R agentuser:agentuser /agent

USER agentuser

CMD ["python", "app/main.py"]
