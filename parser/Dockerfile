ARG IMAGE_WITH_MODELS=telegram-parser-api-python-with-shared-models
FROM $IMAGE_WITH_MODELS

WORKDIR /app

# mysql
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    libmariadb-dev-compat \
    pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install telegram/opentele
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "run.py"]