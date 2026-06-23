FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Reuse the backend stack for the sentence-transformer encoder used by justice embeddings.
COPY backend/requirements.txt /tmp/backend-req.txt
RUN pip install --upgrade pip && pip install -r /tmp/backend-req.txt

COPY scotus/requirements.txt /tmp/scotus-req.txt
RUN pip install -r /tmp/scotus-req.txt

COPY backend /app/backend
COPY scotus /app/scotus

WORKDIR /app/scotus
EXPOSE 8002
CMD ["uvicorn", "scotusapp.main:app", "--host", "0.0.0.0", "--port", "8002"]
