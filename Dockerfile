FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libsndfile1 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["jarvis"]
