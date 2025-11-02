FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for pyfluidsynth / audio backends
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fluid-synth \
        libfluidsynth3 \
        libfluidsynth-dev \
        libsndfile1 \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
