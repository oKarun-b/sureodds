FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=Africa/Douala
COPY pyproject.toml uv.lock* README.md ./
COPY src ./src
COPY config.yaml ./
COPY migrations ./migrations
RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "sureodds", "run"]
