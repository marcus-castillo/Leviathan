FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /work

RUN apt-get update && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

# Reuse the backend stack (torch, spaCy, sentence-transformers, etc.).
COPY backend/requirements.txt /tmp/backend-req.txt
RUN pip install --upgrade pip && pip install -r /tmp/backend-req.txt
RUN python -m spacy download en_core_web_sm

COPY corpus/requirements.txt /tmp/corpus-req.txt
RUN pip install -r /tmp/corpus-req.txt

COPY backend /work/backend
COPY corpus /work/corpus
RUN pip install -e /work/corpus

WORKDIR /work/corpus
ENTRYPOINT ["levcorpus"]
CMD ["--help"]
