FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.4 \
    OUTPUT_DIR=/app/outputs

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p ${OUTPUT_DIR}

EXPOSE 8501

ENV FAL_KEY=""

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

